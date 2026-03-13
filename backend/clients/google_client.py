"""Google Gemini API client for Nano Banana 2 image and Veo 3.1 video generation.

Uses the google-genai SDK with the Developer API (API key auth).
Image generation: client.aio.models.generate_content with response_modalities=["IMAGE"]
Video generation: client.aio.models.generate_videos → poll operations → download
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from google import genai
from google.genai import types

from backend.clients.base import GenerationResult

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

logger = logging.getLogger(__name__)

# Cost estimates (USD per generation) — approximate
_IMAGE_COSTS: dict[str, float] = {
    "1K": 0.04,
    "2K": 0.08,
    "4K": 0.15,
}

_VIDEO_COST_PER_SECOND = 0.75  # Veo 3 standard
_VIDEO_COST_PER_SECOND_FAST = 0.35  # Veo 3 fast


class GoogleAPIError(Exception):
    """Error from the Google Gemini/Veo API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GoogleClient:
    """Client for Google image (Nano Banana 2) and video (Veo 3.1) generation."""

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._poll_interval = 15.0
        self._max_poll_time = 600.0  # 10 min timeout

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        resolution: str = "1K",
    ) -> GenerationResult:
        """Generate an image using Gemini (Nano Banana 2).

        Args:
            prompt: Text description of the image to generate.
            aspect_ratio: One of "1:1", "9:16", "16:9", "3:4", "4:3".
            resolution: One of "1K", "2K", "4K".

        Returns:
            GenerationResult with PNG image bytes.
        """
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=resolution,
            ),
        )

        try:
            response = await self._client.aio.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            raise GoogleAPIError(f"Image generation failed: {exc}") from exc

        # Extract image from response parts
        if not response.parts:
            raise GoogleAPIError("No parts in image generation response")

        for part in response.parts:
            if part.inline_data is not None:
                # inline_data is a Blob with .data (raw bytes) and .mime_type
                raw_bytes = part.inline_data.data
                if raw_bytes is None:
                    continue
                mime = part.inline_data.mime_type or "image/png"

                return GenerationResult(
                    data=raw_bytes,
                    cost_estimate=_IMAGE_COSTS.get(resolution, 0.04),
                    media_type=mime,
                )

        raise GoogleAPIError("No image data found in response parts")

    async def generate_video(
        self,
        prompt: str,
        image: Any | None = None,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        progress_callback: Callable[[int, int], Coroutine[Any, Any, None]] | None = None,
    ) -> GenerationResult:
        """Generate a video using Veo 3.1.

        Args:
            prompt: Text description of the video to generate.
            image: Optional PIL Image for image-to-video.
            duration: Video duration in seconds (5-8).
            aspect_ratio: "16:9" or "9:16".
            progress_callback: async callback(current, total) for progress updates.

        Returns:
            GenerationResult with MP4 video bytes.
        """
        config = types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            number_of_videos=1,
            duration_seconds=duration,
            person_generation="allow_adult",
        )

        try:
            operation = await self._client.aio.models.generate_videos(
                model="veo-3.1-generate-preview",
                prompt=prompt,
                image=image,
                config=config,
            )
        except Exception as exc:
            raise GoogleAPIError(f"Video generation request failed: {exc}") from exc

        # Poll until done
        start_time = time.monotonic()
        poll_count = 0

        while not operation.done:
            elapsed = time.monotonic() - start_time
            if elapsed > self._max_poll_time:
                raise GoogleAPIError(
                    f"Video generation timed out after {self._max_poll_time}s"
                )

            # Estimate progress based on elapsed time vs expected duration
            estimated_total = 180  # ~3 min typical
            progress_pct = min(int((elapsed / estimated_total) * 100), 95)
            if progress_callback is not None:
                await progress_callback(progress_pct, 100)

            await asyncio.sleep(self._poll_interval)
            poll_count += 1

            try:
                operation = await self._client.aio.operations.get(operation)
            except Exception as exc:
                raise GoogleAPIError(f"Failed to poll video operation: {exc}") from exc

        if progress_callback is not None:
            await progress_callback(100, 100)

        # Download the generated video
        try:
            resp = operation.response
            if resp is None or not resp.generated_videos:
                raise GoogleAPIError("No videos in generation response")

            video_obj = resp.generated_videos[0].video
            if video_obj is None:
                raise GoogleAPIError("No video file in generation response")

            await self._client.aio.files.download(file=video_obj)  # type: ignore[arg-type]

            # After download, video_bytes is populated
            video_bytes = video_obj.video_bytes
            if video_bytes is None:
                raise GoogleAPIError("Downloaded video has no bytes")

        except GoogleAPIError:
            raise
        except Exception as exc:
            raise GoogleAPIError(f"Failed to download generated video: {exc}") from exc

        cost = duration * _VIDEO_COST_PER_SECOND

        return GenerationResult(
            data=video_bytes,
            cost_estimate=cost,
            media_type="video/mp4",
            duration_seconds=float(duration),
        )
