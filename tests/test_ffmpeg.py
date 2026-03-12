import json
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from backend.clients.ffmpeg_client import (
    FFmpegError,
    VideoInfo,
    concatenate_videos,
    extract_last_frame,
    get_video_info,
    normalize_video,
)


def _mock_proc(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> AsyncMock:
    proc = AsyncMock()
    proc.communicate.return_value = (stdout, stderr)
    proc.returncode = returncode
    return proc


@pytest.fixture
def mock_subprocess() -> Generator[AsyncMock]:
    with patch("backend.clients.ffmpeg_client.asyncio.create_subprocess_exec") as m:
        yield m


class TestGetVideoInfo:
    async def test_returns_video_info(self, mock_subprocess: AsyncMock) -> None:
        probe_output = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "24/1",
                }
            ],
            "format": {"duration": "10.5"},
        }
        mock_subprocess.return_value = _mock_proc(stdout=json.dumps(probe_output).encode())

        info = await get_video_info("/test/video.mp4")

        assert info == VideoInfo(width=1920, height=1080, duration=10.5, fps=24.0, codec="h264")
        args = mock_subprocess.call_args[0]
        assert args[0] == "ffprobe"
        assert "-print_format" in args
        assert "json" in args

    async def test_raises_on_failure(self, mock_subprocess: AsyncMock) -> None:
        mock_subprocess.return_value = _mock_proc(
            stderr=b"No such file", returncode=1
        )
        with pytest.raises(FFmpegError) as exc_info:
            await get_video_info("/missing.mp4")
        assert "No such file" in exc_info.value.stderr


class TestExtractLastFrame:
    async def test_correct_args(self, mock_subprocess: AsyncMock) -> None:
        mock_subprocess.return_value = _mock_proc()

        result = await extract_last_frame("/vid.mp4", "/frame.png")

        from pathlib import Path

        assert result == Path("/frame.png")
        args = mock_subprocess.call_args[0]
        assert "-sseof" in args
        assert "-0.1" in args
        assert "-frames:v" in args


class TestNormalizeVideo:
    async def test_correct_args(self, mock_subprocess: AsyncMock) -> None:
        mock_subprocess.return_value = _mock_proc()

        result = await normalize_video("/in.mp4", "/out.mp4", 1280, 720, 30)

        from pathlib import Path

        assert result == Path("/out.mp4")
        args = mock_subprocess.call_args[0]
        assert "libx264" in args
        assert "-r" in args
        idx = list(args).index("-r")
        assert args[idx + 1] == "30"


class TestConcatenateVideos:
    async def test_correct_args(self, mock_subprocess: AsyncMock) -> None:
        mock_subprocess.return_value = _mock_proc()

        result = await concatenate_videos(["/a.mp4", "/b.mp4"], "/out.mp4")

        from pathlib import Path

        assert result == Path("/out.mp4")
        args = mock_subprocess.call_args[0]
        assert "-f" in args
        assert "concat" in args

    async def test_raises_on_failure(self, mock_subprocess: AsyncMock) -> None:
        mock_subprocess.return_value = _mock_proc(stderr=b"error", returncode=1)
        with pytest.raises(FFmpegError):
            await concatenate_videos(["/a.mp4"], "/out.mp4")
