"""Tests for GoogleClient — image (Nano Banana 2) and video (Veo 3.1) generation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from backend.clients.google_client import (
    _IMAGE_COSTS,
    _VIDEO_COST_PER_SECOND,
    GoogleAPIError,
    GoogleClient,
)


@pytest.fixture
def client() -> GoogleClient:
    return GoogleClient(api_key="test-api-key")


_FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-png-image-data"


def _make_image_response(has_image: bool = True) -> MagicMock:
    """Create a mock GenerateContentResponse with an image part."""
    response = MagicMock()
    if has_image:
        part = MagicMock()
        # inline_data is a Blob with .data (bytes) and .mime_type
        part.inline_data.data = _FAKE_PNG_BYTES
        part.inline_data.mime_type = "image/png"
        response.parts = [part]
    else:
        response.parts = []
    return response


def _make_video_operation(done: bool = False) -> MagicMock:
    """Create a mock GenerateVideosOperation."""
    operation = MagicMock()
    operation.done = done
    if done:
        video_file = MagicMock()
        video_file.video_bytes = b"fake-mp4-data"
        generated_video = MagicMock()
        generated_video.video = video_file
        operation.response.generated_videos = [generated_video]
    return operation


class TestGenerateImage:
    async def test_generate_image_success(self, client: GoogleClient) -> None:
        mock_response = _make_image_response(has_image=True)
        client._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await client.generate_image("a red square")

        assert result.media_type == "image/png"
        assert result.data == _FAKE_PNG_BYTES

    async def test_generate_image_aspect_ratios(self, client: GoogleClient) -> None:
        for ratio in ["1:1", "9:16", "16:9", "3:4", "4:3"]:
            mock_response = _make_image_response()
            client._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            await client.generate_image("test", aspect_ratio=ratio)

            call_kwargs = client._client.aio.models.generate_content.call_args
            config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
            assert config.image_config.aspect_ratio == ratio

    async def test_generate_image_resolutions(self, client: GoogleClient) -> None:
        for res in ["1K", "2K", "4K"]:
            mock_response = _make_image_response()
            client._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await client.generate_image("test", resolution=res)

            assert result.cost_estimate == _IMAGE_COSTS[res]

    async def test_generate_image_no_image_in_response(self, client: GoogleClient) -> None:
        mock_response = _make_image_response(has_image=False)
        client._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with pytest.raises(GoogleAPIError, match="No parts"):
            await client.generate_image("test")

    async def test_generate_image_no_inline_data(self, client: GoogleClient) -> None:
        response = MagicMock()
        text_part = MagicMock()
        text_part.inline_data = None
        response.parts = [text_part]
        client._client.aio.models.generate_content = AsyncMock(return_value=response)

        with pytest.raises(GoogleAPIError, match="No image data"):
            await client.generate_image("test")

    async def test_generate_image_api_error(self, client: GoogleClient) -> None:
        client._client.aio.models.generate_content = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )

        with pytest.raises(GoogleAPIError, match="rate limit"):
            await client.generate_image("test")

    async def test_cost_estimates_image(self, client: GoogleClient) -> None:
        assert _IMAGE_COSTS["1K"] == 0.04
        assert _IMAGE_COSTS["2K"] == 0.08
        assert _IMAGE_COSTS["4K"] == 0.15


class TestGenerateVideo:
    async def test_generate_video_success(self, client: GoogleClient) -> None:
        # First call returns not done, second returns done
        op_pending = _make_video_operation(done=False)
        op_done = _make_video_operation(done=True)

        client._client.aio.models.generate_videos = AsyncMock(return_value=op_pending)
        client._client.aio.operations.get = AsyncMock(return_value=op_done)
        client._client.aio.files.download = AsyncMock(return_value=b"fake-mp4-data")
        client._poll_interval = 0.01  # Speed up test

        result = await client.generate_video("a sunset scene")

        assert result.media_type == "video/mp4"
        assert result.data == b"fake-mp4-data"
        assert result.duration_seconds == 8.0
        assert result.cost_estimate == 8 * _VIDEO_COST_PER_SECOND

    async def test_generate_video_polling(self, client: GoogleClient) -> None:
        op_pending = _make_video_operation(done=False)
        op_still_pending = _make_video_operation(done=False)
        op_done = _make_video_operation(done=True)

        client._client.aio.models.generate_videos = AsyncMock(return_value=op_pending)
        client._client.aio.operations.get = AsyncMock(
            side_effect=[op_still_pending, op_still_pending, op_done]
        )
        client._client.aio.files.download = AsyncMock(return_value=b"fake-mp4-data")
        client._poll_interval = 0.01

        result = await client.generate_video("test")

        assert client._client.aio.operations.get.call_count == 3
        assert result.data == b"fake-mp4-data"

    async def test_generate_video_progress_callback(self, client: GoogleClient) -> None:
        op_pending = _make_video_operation(done=False)
        op_done = _make_video_operation(done=True)

        client._client.aio.models.generate_videos = AsyncMock(return_value=op_pending)
        client._client.aio.operations.get = AsyncMock(return_value=op_done)
        client._client.aio.files.download = AsyncMock(return_value=b"fake-mp4-data")
        client._poll_interval = 0.01

        progress_calls: list[tuple[int, int]] = []

        async def track_progress(current: int, total: int) -> None:
            progress_calls.append((current, total))

        await client.generate_video("test", progress_callback=track_progress)

        # Should have at least the final 100% call
        assert any(c == (100, 100) for c in progress_calls)

    async def test_generate_video_with_image(self, client: GoogleClient) -> None:
        op_done = _make_video_operation(done=True)
        op_done.done = True

        client._client.aio.models.generate_videos = AsyncMock(return_value=op_done)
        client._client.aio.files.download = AsyncMock(return_value=b"fake-mp4-data")
        client._poll_interval = 0.01

        ref_image = Image.new("RGB", (128, 128), color="blue")
        await client.generate_video("test", image=ref_image)

        call_kwargs = client._client.aio.models.generate_videos.call_args
        veo_image = call_kwargs.kwargs.get("image")
        assert veo_image is not None
        assert veo_image.mime_type == "image/png"
        assert veo_image.image_bytes is not None

    async def test_generate_video_timeout(self, client: GoogleClient) -> None:
        op_pending = _make_video_operation(done=False)

        client._client.aio.models.generate_videos = AsyncMock(return_value=op_pending)
        client._client.aio.operations.get = AsyncMock(return_value=op_pending)
        client._poll_interval = 0.01
        client._max_poll_time = 0.05  # Very short timeout

        with pytest.raises(GoogleAPIError, match="timed out"):
            await client.generate_video("test")

    async def test_generate_video_api_error(self, client: GoogleClient) -> None:
        client._client.aio.models.generate_videos = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        with pytest.raises(GoogleAPIError, match="Service unavailable"):
            await client.generate_video("test")

    async def test_generate_video_poll_error(self, client: GoogleClient) -> None:
        op_pending = _make_video_operation(done=False)

        client._client.aio.models.generate_videos = AsyncMock(return_value=op_pending)
        client._client.aio.operations.get = AsyncMock(
            side_effect=Exception("Network error")
        )
        client._poll_interval = 0.01

        with pytest.raises(GoogleAPIError, match="Failed to poll"):
            await client.generate_video("test")

    async def test_generate_video_no_videos_in_response(self, client: GoogleClient) -> None:
        op_done = MagicMock()
        op_done.done = True
        op_done.response.generated_videos = []

        client._client.aio.models.generate_videos = AsyncMock(return_value=op_done)
        client._client.aio.files.download = AsyncMock()
        client._poll_interval = 0.01

        with pytest.raises(GoogleAPIError, match="No videos"):
            await client.generate_video("test")

    async def test_generate_video_duration_affects_cost(self, client: GoogleClient) -> None:
        op_done = _make_video_operation(done=True)
        client._client.aio.models.generate_videos = AsyncMock(return_value=op_done)
        client._client.aio.files.download = AsyncMock(return_value=b"fake-mp4-data")

        result = await client.generate_video("test", duration=5)

        # duration=5 snaps to 4 via _snap_veo_duration
        assert result.cost_estimate == 4 * _VIDEO_COST_PER_SECOND
        assert result.duration_seconds == 4.0

    async def test_cost_estimates_video(self) -> None:
        assert _VIDEO_COST_PER_SECOND == 0.75
