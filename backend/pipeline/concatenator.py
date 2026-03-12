from pathlib import Path

from backend.clients.ffmpeg_client import concatenate_videos, normalize_video


async def concatenate_project(
    project_id: str,
    shot_paths: list[Path],
    output_dir: Path,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
) -> Path:
    """Concatenate all shot videos into a single final output."""
    final_dir = output_dir / project_id / "final"
    final_dir.mkdir(parents=True, exist_ok=True)

    if len(shot_paths) == 1:
        # Single shot — just normalize to target spec
        final_path = final_dir / "final.mp4"
        await normalize_video(shot_paths[0], final_path, width=width, height=height, fps=fps)
        return final_path

    # Normalize each shot to consistent resolution/fps
    normalized: list[str | Path] = []
    for i, shot_path in enumerate(shot_paths):
        norm_path = final_dir / f"norm_{i:02d}.mp4"
        await normalize_video(shot_path, norm_path, width=width, height=height, fps=fps)
        normalized.append(norm_path)

    # Concatenate all normalized clips
    final_path = final_dir / "final.mp4"
    await concatenate_videos(normalized, final_path)

    # Clean up normalized intermediates
    for p in normalized:
        Path(p).unlink(missing_ok=True)

    return final_path
