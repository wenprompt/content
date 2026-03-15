import asyncio
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path


class FFmpegError(Exception):
    def __init__(self, message: str, stderr: str = "") -> None:
        self.message = message
        self.stderr = stderr
        super().__init__(message)


@dataclass
class VideoInfo:
    width: int
    height: int
    duration: float
    fps: float
    codec: str


async def _run(
    program: str, *args: str, timeout: float = 300.0
) -> tuple[bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        program,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise FFmpegError(f"{program} timed out after {timeout}s") from None
    if proc.returncode != 0:
        raise FFmpegError(
            f"{program} exited with code {proc.returncode}",
            stderr=stderr.decode(errors="replace"),
        )
    return stdout, stderr


async def get_video_info(path: str | Path) -> VideoInfo:
    stdout, _ = await _run(
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    )
    data = json.loads(stdout)
    stream = next(s for s in data["streams"] if s["codec_type"] == "video")

    # Parse fps from r_frame_rate fraction like "24/1"
    num, den = stream["r_frame_rate"].split("/")
    fps = float(num) / float(den)

    return VideoInfo(
        width=int(stream["width"]),
        height=int(stream["height"]),
        duration=float(data["format"]["duration"]),
        fps=fps,
        codec=stream["codec_name"],
    )


async def extract_last_frame(video_path: str | Path, output_path: str | Path) -> Path:
    out = Path(output_path)
    await _run(
        "ffmpeg", "-y",
        "-sseof", "-0.1",
        "-i", str(video_path),
        "-frames:v", "1",
        "-update", "1",
        str(out),
    )
    return out


async def normalize_video(
    path: str | Path,
    output: str | Path,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
) -> Path:
    out = Path(output)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    )
    await _run(
        "ffmpeg", "-y",
        "-i", str(path),
        "-vf", vf,
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "128k",
        str(out),
    )
    return out


async def concatenate_videos(paths: list[str | Path], output: str | Path) -> Path:
    out = Path(output)
    # Write concat list to a temp file. Use delete=False and close before
    # passing to ffmpeg — on Windows, NamedTemporaryFile keeps the file
    # locked while open, preventing ffmpeg from reading it.
    concat_file = tempfile.mktemp(suffix=".txt")  # noqa: S324
    try:
        Path(concat_file).write_text(
            "".join(f"file '{Path(p).resolve().as_posix()}'\n" for p in paths),
            encoding="utf-8",
        )
        await _run(
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            str(out),
        )
    finally:
        Path(concat_file).unlink(missing_ok=True)

    return out
