"""OpenAI API client for GPT Image and Sora 2 video generation.

Uses the openai SDK with AsyncOpenAI.
Image generation: Responses API with image_generation tool
Video generation: Videos API with manual polling for progress callbacks
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

import openai

from backend.clients.base import GenerationResult

logger = logging.getLogger(__name__)

# Cost estimates (USD) — approximate
_IMAGE_COSTS: dict[str, dict[str, float]] = {
    "low": {"1024x1024": 0.02, "1024x1536": 0.03, "1536x1024": 0.03},
    "medium": {"1024x1024": 0.04, "1024x1536": 0.06, "1536x1024": 0.06},
    "high": {"1024x1024": 0.08, "1024x1536": 0.12, "1536x1024": 0.12},
}

_VIDEO_COSTS: dict[str, dict[int, float]] = {
    "sora-2": {4: 0.20, 8: 0.40, 12: 0.60},
    "sora-2-pro": {4: 0.60, 8: 1.20, 12: 1.80},
}


class OpenAIAPIError(Exception):
    """Error from the OpenAI API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenAIClient:
    """Client for OpenAI image (GPT Image) and video (Sora 2) generation."""

    def __init__(self, api_key: str) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._poll_interval = 10.0
        self._max_poll_time = 600.0  # 10 min timeout

    async def generate_image(
        self,
        prompt: str,
        model: str = "gpt-4.1-mini",
        size: str = "1024x1024",
        quality: str = "medium",
    ) -> GenerationResult:
        """Generate an image using GPT Image via the Responses API.

        Args:
            prompt: Text description of the image.
            model: Model to use (e.g. "gpt-4.1-mini", "gpt-4.1").
            size: Image size ("1024x1024", "1024x1536", "1536x1024").
            quality: Quality level ("low", "medium", "high").

        Returns:
            GenerationResult with PNG image bytes.
        """
        tool_config: dict[str, Any] = {
            "type": "image_generation",
            "size": size,
            "quality": quality,
            "output_format": "png",
        }

        try:
            response = await self._client.responses.create(
                model=model,
                input=prompt,
                tools=[tool_config],  # type: ignore[list-item]
            )
        except Exception as exc:
            raise OpenAIAPIError(f"Image generation failed: {exc}") from exc

        # Extract base64 image from response output
        for output in response.output:
            if output.type == "image_generation_call":
                if output.result is None:
                    continue
                image_bytes = base64.b64decode(output.result)
                cost = _IMAGE_COSTS.get(quality, {}).get(size, 0.04)

                return GenerationResult(
                    data=image_bytes,
                    cost_estimate=cost,
                    media_type="image/png",
                )

        raise OpenAIAPIError("No image data found in response output")

    async def generate_video(
        self,
        prompt: str,
        image: Any | None = None,
        model: str = "sora-2",
        duration: int = 10,
        resolution: str = "720p",
        progress_callback: Callable[[int, int], Coroutine[Any, Any, None]] | None = None,
    ) -> GenerationResult:
        """Generate a video using Sora 2.

        Args:
            prompt: Text description of the video.
            image: Optional reference image for image-to-video (unused for now).
            model: "sora-2" or "sora-2-pro".
            duration: Video duration in seconds.
            resolution: "480p", "720p", or "1080p".
            progress_callback: async callback(current, total) for progress updates.

        Returns:
            GenerationResult with MP4 video bytes.
        """
        # Map resolution to size
        size = _resolution_to_size(resolution)

        # Map duration to supported values (4, 8, 12)
        seconds = _snap_duration(duration)

        create_kwargs: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "seconds": seconds,
            "size": size,
        }

        try:
            video = await self._client.videos.create(**create_kwargs)
        except Exception as exc:
            raise OpenAIAPIError(f"Video generation request failed: {exc}") from exc

        # Poll until done
        start_time = time.monotonic()

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > self._max_poll_time:
                raise OpenAIAPIError(
                    f"Video generation timed out after {self._max_poll_time}s"
                )

            try:
                video = await self._client.videos.retrieve(video.id)
            except Exception as exc:
                raise OpenAIAPIError(f"Failed to poll video status: {exc}") from exc

            if video.status == "completed":
                break
            elif video.status == "failed":
                error_msg = str(video.error) if video.error else "Unknown error"
                raise OpenAIAPIError(f"Video generation failed: {error_msg}")

            # Report progress from API
            progress = getattr(video, "progress", None) or 0
            if progress_callback is not None:
                await progress_callback(int(progress), 100)

            await asyncio.sleep(self._poll_interval)

        if progress_callback is not None:
            await progress_callback(100, 100)

        # Download video bytes
        try:
            content = await self._client.videos.download_content(video.id)
            video_bytes: bytes = content.content
        except Exception as exc:
            raise OpenAIAPIError(f"Failed to download video: {exc}") from exc

        model_costs = _VIDEO_COSTS.get(model, _VIDEO_COSTS["sora-2"])
        cost = model_costs.get(seconds, 0.40)

        return GenerationResult(
            data=video_bytes,
            cost_estimate=cost,
            media_type="video/mp4",
            duration_seconds=float(seconds),
        )


def _resolution_to_size(resolution: str) -> str:
    """Map resolution string to OpenAI size parameter."""
    mapping = {
        "480p": "1024x1024",
        "720p": "1280x720",
        "1080p": "1792x1024",
    }
    return mapping.get(resolution, "1280x720")


def _snap_duration(duration: int) -> int:
    """Snap duration to nearest supported Sora value (4, 8, 12)."""
    if duration <= 6:
        return 4
    elif duration <= 10:
        return 8
    else:
        return 12
