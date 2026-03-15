"""Tests for Gemini video analyzer."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE_ANALYSIS: dict[str, Any] = {
    "hook_analysis": {
        "visual_element": "product close-up",
        "camera_angle": "low angle",
        "timing_seconds": 1.5,
    },
    "visual_style": {
        "color_palette": ["#FF5733", "#33FF57", "#3357FF"],
        "lighting": "warm golden hour",
        "aesthetic": "modern minimalist",
    },
    "camera_work": {
        "shot_types": ["close-up", "wide", "medium"],
        "movements": ["dolly_in", "static", "dolly_out"],
        "transitions": ["cut", "dissolve"],
        "avg_shot_duration": 3.0,
    },
    "pacing": {
        "tempo": "fast",
        "energy_curve": "builds",
        "number_of_cuts": 8,
        "total_duration": 15.0,
    },
    "audio": {
        "music_genre": "electronic",
        "music_tempo_bpm": 128,
        "sound_effects": ["whoosh", "impact"],
        "audio_visual_sync": "tight",
    },
    "content_structure": {
        "pattern": "hook-setup-payoff",
        "format_type": "showcase",
    },
    "product_presentation": {
        "appearance_method": "hero reveal at 3 seconds",
        "features_highlighted": ["design", "portability"],
    },
    "engagement_drivers": {
        "shareability_factor": "satisfying reveal",
        "emotional_trigger": "curiosity",
        "cta": "link in bio",
    },
    "shot_breakdown": [
        {
            "timestamp": "0:00-0:03",
            "description": "Hook shot with dramatic lighting",
            "camera_movement": "dolly_in",
            "duration_sec": 3.0,
        },
        {
            "timestamp": "0:03-0:07",
            "description": "Product reveal wide shot",
            "camera_movement": "static",
            "duration_sec": 4.0,
        },
    ],
}


class TestGeminiAnalyzer:
    async def test_analyze_video_success(self) -> None:
        from backend.trend_intelligence.analyzers.gemini_analyzer import analyze_video

        mock_uploaded = MagicMock()
        mock_uploaded.name = "files/test-123"
        mock_uploaded.uri = "https://storage.googleapis.com/files/test-123"
        mock_uploaded.mime_type = "video/mp4"

        mock_file_status = MagicMock()
        mock_file_status.state = "ACTIVE"

        mock_response = MagicMock()
        mock_response.text = json.dumps(SAMPLE_ANALYSIS)

        mock_aio = MagicMock()
        mock_aio.files = MagicMock()
        mock_aio.files.upload = AsyncMock(return_value=mock_uploaded)
        mock_aio.files.get = AsyncMock(return_value=mock_file_status)
        mock_aio.files.delete = AsyncMock()
        mock_aio.models = MagicMock()
        mock_aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("backend.trend_intelligence.analyzers.gemini_analyzer.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.aio = mock_aio
            mock_genai.Client.return_value = mock_client

            result = await analyze_video("/tmp/test.mp4", api_key="test-key")

        assert result["hook_analysis"]["visual_element"] == "product close-up"
        assert len(result["shot_breakdown"]) == 2
        assert result["pacing"]["tempo"] == "fast"

        # Verify cleanup was called
        mock_aio.files.delete.assert_called_once_with(name="files/test-123")

    async def test_analyze_video_empty_response(self) -> None:
        from backend.trend_intelligence.analyzers.gemini_analyzer import analyze_video

        mock_uploaded = MagicMock()
        mock_uploaded.name = "files/test-123"
        mock_uploaded.uri = "https://storage.googleapis.com/files/test-123"
        mock_uploaded.mime_type = "video/mp4"

        mock_file_status = MagicMock()
        mock_file_status.state = "ACTIVE"

        mock_response = MagicMock()
        mock_response.text = ""

        mock_aio = MagicMock()
        mock_aio.files = MagicMock()
        mock_aio.files.upload = AsyncMock(return_value=mock_uploaded)
        mock_aio.files.get = AsyncMock(return_value=mock_file_status)
        mock_aio.files.delete = AsyncMock()
        mock_aio.models = MagicMock()
        mock_aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("backend.trend_intelligence.analyzers.gemini_analyzer.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.aio = mock_aio
            mock_genai.Client.return_value = mock_client

            with pytest.raises(ValueError, match="Empty response"):
                await analyze_video("/tmp/test.mp4", api_key="test-key")

        # Cleanup should still happen
        mock_aio.files.delete.assert_called_once()

    async def test_analyze_video_timeout(self) -> None:
        from backend.trend_intelligence.analyzers.gemini_analyzer import analyze_video

        mock_uploaded = MagicMock()
        mock_uploaded.name = "files/test-123"
        mock_uploaded.uri = "https://storage.googleapis.com/files/test-123"
        mock_uploaded.mime_type = "video/mp4"

        mock_file_status = MagicMock()
        mock_file_status.state = "PROCESSING"  # Never becomes ACTIVE

        mock_aio = MagicMock()
        mock_aio.files = MagicMock()
        mock_aio.files.upload = AsyncMock(return_value=mock_uploaded)
        mock_aio.files.get = AsyncMock(return_value=mock_file_status)
        mock_aio.files.delete = AsyncMock()

        with (
            patch("backend.trend_intelligence.analyzers.gemini_analyzer.genai") as mock_genai,
            patch("backend.trend_intelligence.analyzers.gemini_analyzer.asyncio") as mock_asyncio,
        ):
            mock_client = MagicMock()
            mock_client.aio = mock_aio
            mock_genai.Client.return_value = mock_client
            mock_asyncio.sleep = AsyncMock()

            with pytest.raises(TimeoutError, match="did not become ACTIVE"):
                await analyze_video("/tmp/test.mp4", api_key="test-key")


class TestDownloadVideo:
    async def test_download_direct_success(self, tmp_path: Path) -> None:
        from backend.trend_intelligence.analyzers.gemini_analyzer import download_video

        mock_response = MagicMock()
        mock_response.content = b"fake video bytes"
        mock_response.raise_for_status = MagicMock()

        patch_target = "backend.trend_intelligence.analyzers.gemini_analyzer.httpx.AsyncClient"
        with patch(patch_target) as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_client

            result = await download_video(
                "https://example.com/video.mp4", tmp_path
            )

        assert result.exists()
        assert result.name == "video.mp4"
        assert result.read_bytes() == b"fake video bytes"

    async def test_download_direct_no_extension(self, tmp_path: Path) -> None:
        from backend.trend_intelligence.analyzers.gemini_analyzer import download_video

        mock_response = MagicMock()
        mock_response.content = b"data"
        mock_response.raise_for_status = MagicMock()

        patch_target = "backend.trend_intelligence.analyzers.gemini_analyzer.httpx.AsyncClient"
        with patch(patch_target) as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_client

            result = await download_video(
                "https://example.com/download", tmp_path
            )

        assert result.name == "downloaded_video.mp4"

    async def test_download_tiktok_uses_ytdlp(self, tmp_path: Path) -> None:
        from backend.trend_intelligence.analyzers.gemini_analyzer import download_video

        video_file = tmp_path / "12345.mp4"
        video_file.write_bytes(b"tiktok video data")

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(str(video_file).encode(), b"")
        )

        with patch(
            "backend.trend_intelligence.analyzers.gemini_analyzer.asyncio"
        ) as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=mock_process)
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = asyncio.subprocess.PIPE

            result = await download_video(
                "https://tiktok.com/@user/video/12345", tmp_path
            )

        assert result == video_file
        mock_asyncio.create_subprocess_exec.assert_called_once()
        call_args = mock_asyncio.create_subprocess_exec.call_args[0]
        assert call_args[0] == "yt-dlp"
        assert "https://tiktok.com/@user/video/12345" in call_args

    async def test_download_ytdlp_failure(self, tmp_path: Path) -> None:
        from backend.trend_intelligence.analyzers.gemini_analyzer import download_video

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"ERROR: Video not found")
        )

        with patch(
            "backend.trend_intelligence.analyzers.gemini_analyzer.asyncio"
        ) as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=mock_process)
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = asyncio.subprocess.PIPE

            with pytest.raises(RuntimeError, match="yt-dlp failed"):
                await download_video(
                    "https://instagram.com/reel/xyz", tmp_path
                )

    async def test_is_social_url_detection(self) -> None:
        from backend.trend_intelligence.analyzers.gemini_analyzer import _is_social_url

        assert _is_social_url("https://tiktok.com/@user/video/123")
        assert _is_social_url("https://www.instagram.com/reel/xyz")
        assert _is_social_url("https://facebook.com/reel/456")
        assert _is_social_url("https://youtube.com/watch?v=abc")
        assert _is_social_url("https://youtu.be/abc")
        assert not _is_social_url("https://example.com/video.mp4")
        assert not _is_social_url("https://cdn.some-site.com/file.mp4")
