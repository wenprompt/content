"""Analyze a video using Google Cloud Video Intelligence API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from google.cloud import videointelligence

logger = logging.getLogger(__name__)


async def analyze_video(video_path: str) -> dict[str, Any]:
    """Analyze a video file using Google Cloud Video Intelligence API.

    Authenticates via GOOGLE_APPLICATION_CREDENTIALS env var.
    Runs all 5 features in one call using input_content (raw bytes, no GCS needed).
    """
    import asyncio

    client = videointelligence.VideoIntelligenceServiceClient()

    video_bytes = Path(video_path).read_bytes()

    features = [
        videointelligence.Feature.SHOT_CHANGE_DETECTION,
        videointelligence.Feature.LABEL_DETECTION,
        videointelligence.Feature.TEXT_DETECTION,
        videointelligence.Feature.OBJECT_TRACKING,
        videointelligence.Feature.LOGO_RECOGNITION,
    ]

    # Start long-running operation
    operation = client.annotate_video(
        request=videointelligence.AnnotateVideoRequest(
            input_content=video_bytes,
            features=features,
        )
    )

    # Poll until complete (timeout 300s)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: operation.result(timeout=300)  # type: ignore[no-untyped-call]
    )

    annotation = result.annotation_results[0]

    return _parse_annotation(annotation)


def _offset_to_seconds(offset: Any) -> float:
    """Convert a protobuf Duration to seconds."""
    return float(offset.seconds) + float(offset.microseconds) / 1_000_000


def _parse_annotation(annotation: Any) -> dict[str, Any]:
    """Parse Video Intelligence annotation results into a structured dict."""
    # Shot boundaries
    shots: list[dict[str, float]] = []
    for shot in annotation.shot_annotations:
        shots.append({
            "start": _offset_to_seconds(shot.start_time_offset),
            "end": _offset_to_seconds(shot.end_time_offset),
        })

    # Labels
    labels: list[dict[str, Any]] = []
    for label in annotation.shot_label_annotations:
        best_confidence = max(
            (seg.confidence for seg in label.segments),
            default=0.0,
        )
        labels.append({
            "name": label.entity.description,
            "confidence": round(best_confidence, 3),
        })

    # Text detection
    text: list[dict[str, Any]] = []
    for text_annotation in annotation.text_annotations:
        content = text_annotation.text
        # Get first segment timestamp
        timestamp = 0.0
        if text_annotation.segments:
            seg = text_annotation.segments[0]
            timestamp = _offset_to_seconds(seg.segment.start_time_offset)
        text.append({
            "content": content,
            "timestamp": timestamp,
        })

    # Object tracking
    objects: list[dict[str, Any]] = []
    for obj in annotation.object_annotations:
        frames: list[dict[str, Any]] = []
        for frame in obj.frames[:10]:  # limit to first 10 frames per object
            box = frame.normalized_bounding_box
            frames.append({
                "time": _offset_to_seconds(frame.time_offset),
                "box": {
                    "left": round(box.left, 3),
                    "top": round(box.top, 3),
                    "right": round(box.right, 3),
                    "bottom": round(box.bottom, 3),
                },
            })
        objects.append({
            "name": obj.entity.description,
            "confidence": round(obj.confidence, 3),
            "frames": frames,
        })

    # Logo recognition
    logos: list[dict[str, Any]] = []
    for logo in annotation.logo_recognition_annotations:
        logo_name = logo.entity.description
        for track in logo.tracks:
            timestamp = _offset_to_seconds(track.segment.start_time_offset)
            logos.append({
                "name": logo_name,
                "timestamp": timestamp,
            })
            break  # just first track per logo

    return {
        "shots": shots,
        "labels": labels,
        "text": text,
        "objects": objects,
        "logos": logos,
    }
