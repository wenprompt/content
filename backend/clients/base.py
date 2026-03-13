from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GenerationResult:
    """Result from a cloud generation API (image or video)."""

    data: bytes
    cost_estimate: float
    media_type: str = "video/mp4"
    duration_seconds: float | None = None
