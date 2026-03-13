"""Tests for OpenAIClient — image (GPT Image) and video (Sora 2) generation."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.clients.openai_client import (
    _IMAGE_COSTS,
    _VIDEO_COSTS,
    OpenAIAPIError,
    OpenAIClient,
    _resolution_to_size,
    _snap_duration,
)


@pytest.fixture
def client() -> OpenAIClient:
    return OpenAIClient(api_key="test-api-key")


def _make_image_response(has_image: bool = True) -> MagicMock:
    """Create a mock Responses API response with an image_generation_call output."""
    response = MagicMock()
    if has_image:
        output_item = MagicMock()
        output_item.type = "image_generation_call"
        # Base64 encode a small fake PNG header
        output_item.result = base64.b64encode(b"\x89PNG\r\n\x1a\nfake-image-data").decode()
        response.output = [output_item]
    else:
        text_item = MagicMock()
        text_item.type = "text"
        response.output = [text_item]
    return response


def _make_video(status: str = "queued", progress: int = 0) -> MagicMock:
    """Create a mock Video object."""
    video = MagicMock()
    video.id = "video-123"
    video.status = status
    video.progress = progress
    video.error = None
    return video


class TestGenerateImage:
    async def test_generate_image_success(self, client: OpenAIClient) -> None:
        mock_response = _make_image_response(has_image=True)
        client._client.responses.create = AsyncMock(return_value=mock_response)

        result = await client.generate_image("a red circle")

        assert result.media_type == "image/png"
        assert len(result.data) > 0
        assert b"\x89PNG" in result.data

    async def test_generate_image_sizes(self, client: OpenAIClient) -> None:
        for size in ["1024x1024", "1024x1536", "1536x1024"]:
            mock_response = _make_image_response()
            client._client.responses.create = AsyncMock(return_value=mock_response)

            await client.generate_image("test", size=size)

            call_kwargs = client._client.responses.create.call_args.kwargs
            tools = call_kwargs["tools"]
            assert tools[0]["size"] == size

    async def test_generate_image_qualities(self, client: OpenAIClient) -> None:
        for quality in ["low", "medium", "high"]:
            mock_response = _make_image_response()
            client._client.responses.create = AsyncMock(return_value=mock_response)

            await client.generate_image("test", quality=quality)

            call_kwargs = client._client.responses.create.call_args.kwargs
            tools = call_kwargs["tools"]
            assert tools[0]["quality"] == quality

    async def test_generate_image_no_image_output(self, client: OpenAIClient) -> None:
        mock_response = _make_image_response(has_image=False)
        client._client.responses.create = AsyncMock(return_value=mock_response)

        with pytest.raises(OpenAIAPIError, match="No image data"):
            await client.generate_image("test")

    async def test_generate_image_api_error(self, client: OpenAIClient) -> None:
        client._client.responses.create = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )

        with pytest.raises(OpenAIAPIError, match="Rate limit"):
            await client.generate_image("test")

    async def test_generate_image_cost_estimate(self, client: OpenAIClient) -> None:
        mock_response = _make_image_response()
        client._client.responses.create = AsyncMock(return_value=mock_response)

        result = await client.generate_image("test", quality="high", size="1024x1536")

        assert result.cost_estimate == _IMAGE_COSTS["high"]["1024x1536"]

    async def test_generate_image_model_forwarding(self, client: OpenAIClient) -> None:
        mock_response = _make_image_response()
        client._client.responses.create = AsyncMock(return_value=mock_response)

        await client.generate_image("test", model="gpt-4.1")

        call_kwargs = client._client.responses.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4.1"


class TestGenerateVideo:
    async def test_generate_video_success(self, client: OpenAIClient) -> None:
        video_queued = _make_video(status="queued", progress=0)
        video_done = _make_video(status="completed", progress=100)

        client._client.videos.create = AsyncMock(return_value=video_queued)
        client._client.videos.retrieve = AsyncMock(return_value=video_done)

        download_content = MagicMock()
        download_content.content = b"fake-mp4-video"
        client._client.videos.download_content = AsyncMock(return_value=download_content)

        client._poll_interval = 0.01

        result = await client.generate_video("a sunset")

        assert result.media_type == "video/mp4"
        assert result.data == b"fake-mp4-video"

    async def test_generate_video_polling_progress(self, client: OpenAIClient) -> None:
        video_queued = _make_video(status="queued", progress=0)
        video_in_progress = _make_video(status="in_progress", progress=50)
        video_done = _make_video(status="completed", progress=100)

        client._client.videos.create = AsyncMock(return_value=video_queued)
        client._client.videos.retrieve = AsyncMock(
            side_effect=[video_in_progress, video_in_progress, video_done]
        )
        download_content = MagicMock()
        download_content.content = b"video-data"
        client._client.videos.download_content = AsyncMock(return_value=download_content)
        client._poll_interval = 0.01

        progress_calls: list[tuple[int, int]] = []

        async def track_progress(current: int, total: int) -> None:
            progress_calls.append((current, total))

        await client.generate_video("test", progress_callback=track_progress)

        # Should have progress calls including intermediate and final
        assert len(progress_calls) >= 2
        assert progress_calls[-1] == (100, 100)
        # Intermediate calls should reflect video.progress
        assert any(c[0] == 50 for c in progress_calls)

    async def test_generate_video_failed_status(self, client: OpenAIClient) -> None:
        video_queued = _make_video(status="queued")
        video_failed = _make_video(status="failed")
        video_failed.error = "Content policy violation"

        client._client.videos.create = AsyncMock(return_value=video_queued)
        client._client.videos.retrieve = AsyncMock(return_value=video_failed)
        client._poll_interval = 0.01

        with pytest.raises(OpenAIAPIError, match="Content policy"):
            await client.generate_video("test")

    async def test_generate_video_timeout(self, client: OpenAIClient) -> None:
        video_queued = _make_video(status="queued")
        video_in_progress = _make_video(status="in_progress", progress=10)

        client._client.videos.create = AsyncMock(return_value=video_queued)
        client._client.videos.retrieve = AsyncMock(return_value=video_in_progress)
        client._poll_interval = 0.01
        client._max_poll_time = 0.05

        with pytest.raises(OpenAIAPIError, match="timed out"):
            await client.generate_video("test")

    async def test_generate_video_models(self, client: OpenAIClient) -> None:
        for model in ["sora-2", "sora-2-pro"]:
            video_done = _make_video(status="completed")
            client._client.videos.create = AsyncMock(return_value=video_done)

            download_content = MagicMock()
            download_content.content = b"data"
            client._client.videos.download_content = AsyncMock(return_value=download_content)

            # Need to make retrieve return completed immediately
            client._client.videos.retrieve = AsyncMock(return_value=video_done)

            result = await client.generate_video("test", model=model, duration=8)

            call_kwargs = client._client.videos.create.call_args.kwargs
            assert call_kwargs["model"] == model
            assert result.cost_estimate == _VIDEO_COSTS[model][8]

    async def test_generate_video_api_error(self, client: OpenAIClient) -> None:
        client._client.videos.create = AsyncMock(
            side_effect=Exception("Server error")
        )

        with pytest.raises(OpenAIAPIError, match="Server error"):
            await client.generate_video("test")

    async def test_generate_video_download_error(self, client: OpenAIClient) -> None:
        video_done = _make_video(status="completed")
        client._client.videos.create = AsyncMock(return_value=video_done)
        client._client.videos.retrieve = AsyncMock(return_value=video_done)
        client._client.videos.download_content = AsyncMock(
            side_effect=Exception("Download failed")
        )

        with pytest.raises(OpenAIAPIError, match="Failed to download"):
            await client.generate_video("test")

    async def test_generate_video_poll_error(self, client: OpenAIClient) -> None:
        video_queued = _make_video(status="queued")
        client._client.videos.create = AsyncMock(return_value=video_queued)
        client._client.videos.retrieve = AsyncMock(
            side_effect=Exception("Network error")
        )
        client._poll_interval = 0.01

        with pytest.raises(OpenAIAPIError, match="Failed to poll"):
            await client.generate_video("test")


class TestHelpers:
    def test_resolution_to_size(self) -> None:
        assert _resolution_to_size("480p") == "1024x1024"
        assert _resolution_to_size("720p") == "1280x720"
        assert _resolution_to_size("1080p") == "1792x1024"
        assert _resolution_to_size("unknown") == "1280x720"

    def test_snap_duration(self) -> None:
        assert _snap_duration(3) == 4
        assert _snap_duration(6) == 4
        assert _snap_duration(7) == 8
        assert _snap_duration(10) == 8
        assert _snap_duration(11) == 12
        assert _snap_duration(15) == 12

    def test_cost_estimates(self) -> None:
        assert _IMAGE_COSTS["low"]["1024x1024"] == 0.02
        assert _IMAGE_COSTS["high"]["1536x1024"] == 0.12
        assert _VIDEO_COSTS["sora-2"][8] == 0.40
        assert _VIDEO_COSTS["sora-2-pro"][8] == 1.20
