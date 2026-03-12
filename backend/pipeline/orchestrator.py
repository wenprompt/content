import asyncio
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.api.websocket import manager
from backend.clients.comfyui_client import ComfyUIClient
from backend.config import get_settings
from backend.database import async_session
from backend.models import Job, Project, Shot
from backend.pipeline.concatenator import concatenate_project

logger = logging.getLogger(__name__)


def _duration_to_frames(duration_sec: float, fps: int = 24) -> int:
    """Convert duration in seconds to a valid LTX frame count.

    Frames must be divisible by 8 + 1 (e.g. 25, 33, 41, ..., 97, 121).
    """
    raw = int(duration_sec * fps)
    # Round to nearest (multiple of 8) + 1
    base = round((raw - 1) / 8) * 8 + 1
    return max(base, 9)  # minimum 9 frames


async def _generate_shot(
    shot: Shot,
    shot_index: int,
    job: Job,
    output_dir: Path,
) -> Path | None:
    """Generate video for a single shot. Returns output path or None."""
    if shot.tool == "ltx":
        settings = get_settings()
        comfyui = ComfyUIClient(settings.comfyui_url)

        async def _progress_cb(step: int, total: int) -> None:
            shot_progress = (step / total) * 100
            await manager.broadcast({
                "type": "shot_step_progress",
                "job_id": job.id,
                "project_id": job.project_id,
                "current_shot_index": shot_index,
                "step": step,
                "total_steps": total,
                "shot_progress": shot_progress,
            })

        video_path = await comfyui.generate_video(
            prompt_text=shot.prompt,
            negative_prompt=shot.negative_prompt,
            width=shot.width,
            height=shot.height,
            num_frames=_duration_to_frames(shot.duration, shot.fps),
            steps=shot.steps,
            cfg=shot.cfg,
            seed=shot.seed,
            fps=shot.fps,
            reference_image=shot.reference_image or None,
            lora_name=shot.lora_name,
            lora_strength=shot.lora_strength,
            progress_callback=_progress_cb,
        )

        # Copy from ComfyUI temp output to project output dir
        project_dir = output_dir / job.project_id / "shots"
        project_dir.mkdir(parents=True, exist_ok=True)
        shot_output = project_dir / f"shot_{shot_index:02d}.mp4"
        shutil.copy2(video_path, shot_output)
        return shot_output

    # Phase 5 will add veo/sora routing
    await asyncio.sleep(1.0)
    return None


async def process_job_queue(app: FastAPI) -> None:
    """Infinite loop: pull job IDs from the queue and process them."""
    while True:
        job_id: str = await app.state.job_queue.get()
        try:
            await _process_job(job_id)
        except Exception:
            logger.exception("Unhandled error in job worker for job %s", job_id)
        finally:
            app.state.job_queue.task_done()


async def _process_job(job_id: str) -> None:
    async with async_session() as session:
        # Load job
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return

        try:
            # Set processing
            job.status = "processing"
            job.message = "Starting generation"
            await session.commit()

            await manager.broadcast({
                "type": "job_progress",
                "job_id": job.id,
                "project_id": job.project_id,
                "progress": 0,
                "current_shot_index": 0,
                "total_shots": job.total_shots,
                "message": job.message,
                "error": None,
                "output_path": None,
            })

            # Set up output directory
            settings = get_settings()
            output_dir = Path(settings.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            shot_paths: list[Path] = []

            # Load project with shots
            proj_result = await session.execute(
                select(Project)
                .where(Project.id == job.project_id)
                .options(selectinload(Project.shots))
            )
            project = proj_result.scalar_one()
            shots = sorted(project.shots, key=lambda s: s.order_index)

            # Process each shot
            for i, shot in enumerate(shots):
                # Re-check for cancellation
                await session.refresh(job)
                if job.status == "cancelled":
                    await manager.broadcast({
                        "type": "job_failed",
                        "job_id": job.id,
                        "project_id": job.project_id,
                        "progress": job.progress,
                        "current_shot_index": i,
                        "total_shots": job.total_shots,
                        "message": "Job cancelled",
                        "error": "cancelled",
                        "output_path": None,
                    })
                    return

                progress = (i / len(shots)) * 100
                job.current_shot_index = i
                job.progress = progress
                job.message = f"Processing shot {i + 1}/{len(shots)}: {shot.name or shot.id}"
                await session.commit()

                await manager.broadcast({
                    "type": "shot_progress",
                    "job_id": job.id,
                    "project_id": job.project_id,
                    "progress": progress,
                    "current_shot_index": i,
                    "total_shots": job.total_shots,
                    "message": job.message,
                    "error": None,
                    "output_path": None,
                })

                # Generate video for this shot
                shot_output = await _generate_shot(
                    shot=shot,
                    shot_index=i,
                    job=job,
                    output_dir=output_dir,
                )
                if shot_output:
                    shot.output_path = str(shot_output)
                    shot_paths.append(shot_output)

                shot.status = "completed"
                await session.commit()

            # Concatenate all shots into final video
            if shot_paths:
                job.message = "Concatenating final video"
                await session.commit()
                final_path = await concatenate_project(
                    project_id=job.project_id,
                    shot_paths=shot_paths,
                    output_dir=output_dir,
                )
                job.output_path = str(final_path)

            # All shots done
            job.status = "completed"
            job.progress = 100
            job.message = "Generation complete"
            job.completed_at = datetime.now(UTC)
            await session.commit()

            await manager.broadcast({
                "type": "job_completed",
                "job_id": job.id,
                "project_id": job.project_id,
                "progress": 100,
                "current_shot_index": len(shots) - 1,
                "total_shots": job.total_shots,
                "message": job.message,
                "error": None,
                "output_path": job.output_path,
            })

        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.message = f"Failed: {exc}"
            await session.commit()

            await manager.broadcast({
                "type": "job_failed",
                "job_id": job.id,
                "project_id": job.project_id,
                "progress": job.progress,
                "current_shot_index": job.current_shot_index,
                "total_shots": job.total_shots,
                "message": job.message,
                "error": str(exc),
                "output_path": None,
            })
