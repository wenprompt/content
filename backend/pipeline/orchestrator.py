from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.api.websocket import manager
from backend.config import get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

    from backend.clients.comfyui_client import ComfyUIClient
    from backend.clients.google_client import GoogleClient
    from backend.clients.openai_client import OpenAIClient
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


def _dimensions_to_aspect(width: int, height: int) -> str:
    """Convert pixel dimensions to an aspect ratio string."""
    ratio = width / height
    if ratio > 1.5:
        return "16:9"
    elif ratio < 0.7:
        return "9:16"
    elif abs(ratio - 1.0) < 0.1:
        return "1:1"
    elif ratio > 1.0:
        return "4:3"
    else:
        return "3:4"


def _dimensions_to_resolution(width: int, height: int) -> str:
    """Convert pixel dimensions to a resolution string for OpenAI."""
    short_side = min(width, height)
    if short_side >= 1080:
        return "1080p"
    elif short_side >= 720:
        return "720p"
    return "480p"


def _dimensions_to_openai_size(width: int, height: int) -> str:
    """Convert pixel dimensions to an OpenAI size string."""
    ratio = width / height
    if ratio > 1.2:
        return "1536x1024"
    elif ratio < 0.8:
        return "1024x1536"
    return "1024x1024"


async def _generate_reference_image(
    prompt: str,
    width: int,
    height: int,
    google_client: GoogleClient | None,
    openai_client: OpenAIClient | None,
) -> Image.Image:
    """Generate a reference image for I2V using the configured default image tool."""
    import io

    settings = get_settings()

    if settings.default_image_tool == "gpt_image":
        if openai_client is None:
            raise RuntimeError("OpenAI API key not configured")
        result = await openai_client.generate_image(
            prompt=prompt,
            size=_dimensions_to_openai_size(width, height),
        )
    else:
        # Default: nano_banana (Google)
        if google_client is None:
            raise RuntimeError("Google API key not configured")
        result = await google_client.generate_image(
            prompt=prompt,
            aspect_ratio=_dimensions_to_aspect(width, height),
        )

    return Image.open(io.BytesIO(result.data))


async def _generate_shot(
    shot: Shot,
    shot_index: int,
    job: Job,
    output_dir: Path,
    app: FastAPI,
) -> Path | None:
    """Generate video for a single shot. Returns output path or None."""
    if shot.tool == "ltx":
        comfyui: ComfyUIClient = app.state.comfyui_client

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

    elif shot.tool == "veo":
        google = app.state.google_client
        if google is None:
            raise RuntimeError("Google API key not configured")

        async def _veo_progress_cb(current: int, total: int) -> None:
            await manager.broadcast({
                "type": "shot_step_progress",
                "job_id": job.id,
                "project_id": job.project_id,
                "current_shot_index": shot_index,
                "step": current,
                "total_steps": total,
                "shot_progress": (current / total) * 100 if total else 0,
            })

        # Generate reference image if I2V but no reference provided
        ref_image = None
        if shot.shot_type == "image_to_video" and not shot.reference_image:
            ref_image = await _generate_reference_image(
                shot.prompt, shot.width, shot.height,
                google_client=app.state.google_client,
                openai_client=app.state.openai_client,
            )
        elif shot.reference_image:
            ref_image = Image.open(shot.reference_image)

        result = await google.generate_video(
            prompt=shot.prompt,
            image=ref_image,
            duration=int(shot.duration),
            aspect_ratio=_dimensions_to_aspect(shot.width, shot.height),
            progress_callback=_veo_progress_cb,
        )

        project_dir = output_dir / job.project_id / "shots"
        project_dir.mkdir(parents=True, exist_ok=True)
        shot_output = project_dir / f"shot_{shot_index:02d}.mp4"
        shot_output.write_bytes(result.data)
        return shot_output

    elif shot.tool == "sora":
        openai_client = app.state.openai_client
        if openai_client is None:
            raise RuntimeError("OpenAI API key not configured")

        async def _sora_progress_cb(current: int, total: int) -> None:
            await manager.broadcast({
                "type": "shot_step_progress",
                "job_id": job.id,
                "project_id": job.project_id,
                "current_shot_index": shot_index,
                "step": current,
                "total_steps": total,
                "shot_progress": (current / total) * 100 if total else 0,
            })

        result = await openai_client.generate_video(
            prompt=shot.prompt,
            duration=int(shot.duration),
            resolution=_dimensions_to_resolution(shot.width, shot.height),
            progress_callback=_sora_progress_cb,
        )

        project_dir = output_dir / job.project_id / "shots"
        project_dir.mkdir(parents=True, exist_ok=True)
        shot_output = project_dir / f"shot_{shot_index:02d}.mp4"
        shot_output.write_bytes(result.data)
        return shot_output

    else:
        raise ValueError(f"Unknown tool: {shot.tool!r}")


async def process_job_queue(app: FastAPI) -> None:
    """Infinite loop: pull job IDs from the queue and process them."""
    while True:
        job_id: str = await app.state.job_queue.get()
        try:
            await _process_job(job_id, app)
        except Exception:
            logger.exception("Unhandled error in job worker for job %s", job_id)
        finally:
            app.state.job_queue.task_done()


async def _process_job(job_id: str, app: FastAPI) -> None:
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
                    app=app,
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
