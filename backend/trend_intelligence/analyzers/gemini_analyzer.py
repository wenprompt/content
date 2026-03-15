"""Analyze a video using Gemini's multimodal capabilities."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path  # noqa: TC003 — used at runtime
from typing import Any

import httpx
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """\
Analyze this video thoroughly across these 8 dimensions. Return ONLY valid JSON.

{
  "hook_analysis": {
    "visual_element": "what visual element stops the scroll",
    "camera_angle": "opening camera angle",
    "timing_seconds": 0.0
  },
  "visual_style": {
    "color_palette": ["#hex1", "#hex2", "#hex3"],
    "lighting": "lighting description",
    "aesthetic": "overall aesthetic description"
  },
  "camera_work": {
    "shot_types": ["close-up", "wide", "etc"],
    "movements": ["dolly_in", "static", "etc"],
    "transitions": ["cut", "dissolve", "etc"],
    "avg_shot_duration": 0.0
  },
  "pacing": {
    "tempo": "fast/medium/slow",
    "energy_curve": "builds/steady/peaks-and-valleys",
    "number_of_cuts": 0,
    "total_duration": 0.0
  },
  "audio": {
    "music_genre": "genre",
    "music_tempo_bpm": 0,
    "sound_effects": ["effect1"],
    "audio_visual_sync": "tight/loose"
  },
  "content_structure": {
    "pattern": "hook-setup-payoff",
    "format_type": "tutorial/showcase/story/montage"
  },
  "product_presentation": {
    "appearance_method": "how product appears",
    "features_highlighted": ["feature1"]
  },
  "engagement_drivers": {
    "shareability_factor": "what makes it shareable",
    "emotional_trigger": "curiosity/excitement/etc",
    "cta": "call to action if any"
  },
  "shot_breakdown": [
    {
      "timestamp": "0:00-0:03",
      "description": "what happens in this shot",
      "camera_movement": "dolly_in",
      "duration_sec": 3.0
    }
  ]
}
"""


_SOCIAL_DOMAINS = ("tiktok.com", "instagram.com", "facebook.com", "youtube.com", "youtu.be")


def _is_social_url(url: str) -> bool:
    """Check if a URL is from a social media platform that needs yt-dlp."""
    return any(domain in url.lower() for domain in _SOCIAL_DOMAINS)


async def download_video(url: str, output_dir: Path) -> Path:
    """Download a video from URL to a temp file.

    Uses yt-dlp for social media URLs (TikTok, Instagram, etc.)
    and direct HTTP download for regular video file URLs.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if _is_social_url(url):
        return await _download_with_ytdlp(url, output_dir)

    return await _download_direct(url, output_dir)


async def _download_with_ytdlp(url: str, output_dir: Path) -> Path:
    """Download video from social media using yt-dlp."""
    output_template = str(output_dir / "%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-warnings",
        "--format", "mp4/best",
        "--output", output_template,
        "--no-playlist",
        "--print", "after_move:filepath",
        url,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        err_msg = stderr.decode().strip()
        raise RuntimeError(f"yt-dlp failed (exit {process.returncode}): {err_msg}")

    filepath = stdout.decode().strip().splitlines()[-1]
    result = Path(filepath)
    if not result.exists():
        raise FileNotFoundError(f"yt-dlp output file not found: {filepath}")

    logger.info("Downloaded video via yt-dlp: %s", result)
    return result


async def _download_direct(url: str, output_dir: Path) -> Path:
    """Download video via direct HTTP GET."""
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

        filename = url.split("/")[-1].split("?")[0]
        if not filename or "." not in filename:
            filename = "downloaded_video.mp4"

        output_path = output_dir / filename
        output_path.write_bytes(response.content)

    return output_path


async def analyze_video(
    video_path: str,
    api_key: str,
    model: str = "gemini-3-pro",
) -> dict[str, Any]:
    """Analyze a video file using Gemini's multimodal capabilities.

    Uploads the video, waits for processing, runs structured analysis,
    and cleans up the uploaded file.
    """
    client = genai.Client(api_key=api_key)

    # Upload video file
    logger.info("Uploading video %s for Gemini analysis", video_path)
    uploaded_file = await client.aio.files.upload(file=video_path)

    # Poll until file is ACTIVE
    file_name = uploaded_file.name or ""
    for _ in range(60):  # max ~5 minutes
        file_status = await client.aio.files.get(name=file_name)
        if file_status.state == "ACTIVE":
            break
        await asyncio.sleep(5)
    else:
        raise TimeoutError(f"Video file {file_name} did not become ACTIVE within timeout")

    try:
        # Run analysis
        video_part = types.Part.from_uri(
            file_uri=uploaded_file.uri or "",
            mime_type=uploaded_file.mime_type or "video/mp4",
        )
        text_part = types.Part.from_text(text=ANALYSIS_PROMPT)
        contents: list[types.Part] = [video_part, text_part]
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,  # type: ignore[arg-type]
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        if not response.text:
            raise ValueError("Empty response from Gemini video analysis")

        parsed: Any = json.loads(response.text)
        # Gemini sometimes wraps the result in an array
        if isinstance(parsed, list) and len(parsed) == 1:
            parsed = parsed[0]
        result: dict[str, Any] = parsed
        return result

    finally:
        # Clean up uploaded file
        try:
            await client.aio.files.delete(name=file_name)
            logger.info("Cleaned up uploaded file %s", file_name)
        except Exception:
            logger.warning("Failed to clean up uploaded file %s", file_name)
