"""Tests for Google Cloud Video Intelligence analyzer."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_duration(seconds: int = 0, microseconds: int = 0) -> MagicMock:
    d = MagicMock()
    d.seconds = seconds
    d.microseconds = microseconds
    return d


def _make_shot(start_sec: int, end_sec: int) -> MagicMock:
    shot = MagicMock()
    shot.start_time_offset = _make_duration(start_sec)
    shot.end_time_offset = _make_duration(end_sec)
    return shot


def _make_label(name: str, confidence: float) -> MagicMock:
    label = MagicMock()
    label.entity = MagicMock()
    label.entity.description = name
    seg = MagicMock()
    seg.confidence = confidence
    label.segments = [seg]
    return label


def _make_text_annotation(content: str, timestamp_sec: int) -> MagicMock:
    text = MagicMock()
    text.text = content
    seg = MagicMock()
    seg.segment = MagicMock()
    seg.segment.start_time_offset = _make_duration(timestamp_sec)
    text.segments = [seg]
    return text


def _make_object_annotation(
    name: str, confidence: float, frame_times: list[int]
) -> MagicMock:
    obj = MagicMock()
    obj.entity = MagicMock()
    obj.entity.description = name
    obj.confidence = confidence
    frames = []
    for t in frame_times:
        frame = MagicMock()
        frame.time_offset = _make_duration(t)
        box = MagicMock()
        box.left = 0.1
        box.top = 0.2
        box.right = 0.5
        box.bottom = 0.8
        frame.normalized_bounding_box = box
        frames.append(frame)
    obj.frames = frames
    return obj


def _make_logo(name: str, timestamp_sec: int) -> MagicMock:
    logo = MagicMock()
    logo.entity = MagicMock()
    logo.entity.description = name
    track = MagicMock()
    track.segment = MagicMock()
    track.segment.start_time_offset = _make_duration(timestamp_sec)
    logo.tracks = [track]
    return logo


def _make_annotation_result() -> MagicMock:
    annotation = MagicMock()
    annotation.shot_annotations = [
        _make_shot(0, 3),
        _make_shot(3, 7),
        _make_shot(7, 15),
    ]
    annotation.shot_label_annotations = [
        _make_label("product", 0.95),
        _make_label("person", 0.88),
    ]
    annotation.text_annotations = [
        _make_text_annotation("BUY NOW", 5),
        _make_text_annotation("Limited Edition", 10),
    ]
    annotation.object_annotations = [
        _make_object_annotation("phone", 0.92, [1, 3, 5]),
    ]
    annotation.logo_recognition_annotations = [
        _make_logo("BrandX", 2),
    ]
    return annotation


class TestVideoIntelligenceAnalyzer:
    async def test_analyze_all_features(self, tmp_path: Any) -> None:
        from backend.trend_intelligence.analyzers.video_intelligence_analyzer import (
            analyze_video,
        )

        # Create a fake video file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video data")

        annotation = _make_annotation_result()

        mock_operation = MagicMock()
        mock_operation.result.return_value = MagicMock()
        mock_operation.result.return_value.annotation_results = [annotation]

        with patch(
            "backend.trend_intelligence.analyzers.video_intelligence_analyzer.videointelligence"
        ) as mock_vi:
            mock_client = MagicMock()
            mock_client.annotate_video.return_value = mock_operation
            mock_vi.VideoIntelligenceServiceClient.return_value = mock_client
            mock_vi.Feature = MagicMock()
            mock_vi.Feature.SHOT_CHANGE_DETECTION = "SHOT_CHANGE_DETECTION"
            mock_vi.Feature.LABEL_DETECTION = "LABEL_DETECTION"
            mock_vi.Feature.TEXT_DETECTION = "TEXT_DETECTION"
            mock_vi.Feature.OBJECT_TRACKING = "OBJECT_TRACKING"
            mock_vi.Feature.LOGO_RECOGNITION = "LOGO_RECOGNITION"
            mock_vi.AnnotateVideoRequest = dict

            result = await analyze_video(str(video_file))

        # Shot boundaries
        assert len(result["shots"]) == 3
        assert result["shots"][0] == {"start": 0.0, "end": 3.0}
        assert result["shots"][2] == {"start": 7.0, "end": 15.0}

        # Labels
        assert len(result["labels"]) == 2
        assert result["labels"][0]["name"] == "product"
        assert result["labels"][0]["confidence"] == 0.95

        # Text
        assert len(result["text"]) == 2
        assert result["text"][0]["content"] == "BUY NOW"
        assert result["text"][0]["timestamp"] == 5.0

        # Objects
        assert len(result["objects"]) == 1
        assert result["objects"][0]["name"] == "phone"
        assert len(result["objects"][0]["frames"]) == 3

        # Logos
        assert len(result["logos"]) == 1
        assert result["logos"][0]["name"] == "BrandX"
        assert result["logos"][0]["timestamp"] == 2.0

    async def test_analyze_timeout(self, tmp_path: Any) -> None:
        from backend.trend_intelligence.analyzers.video_intelligence_analyzer import (
            analyze_video,
        )

        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video data")

        mock_operation = MagicMock()
        mock_operation.result.side_effect = Exception("Timeout exceeded")

        with patch(
            "backend.trend_intelligence.analyzers.video_intelligence_analyzer.videointelligence"
        ) as mock_vi:
            mock_client = MagicMock()
            mock_client.annotate_video.return_value = mock_operation
            mock_vi.VideoIntelligenceServiceClient.return_value = mock_client
            mock_vi.Feature = MagicMock()
            mock_vi.AnnotateVideoRequest = dict

            with pytest.raises(Exception, match="Timeout"):
                await analyze_video(str(video_file))

    async def test_analyze_empty_annotations(self, tmp_path: Any) -> None:
        from backend.trend_intelligence.analyzers.video_intelligence_analyzer import (
            analyze_video,
        )

        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video data")

        annotation = MagicMock()
        annotation.shot_annotations = []
        annotation.shot_label_annotations = []
        annotation.text_annotations = []
        annotation.object_annotations = []
        annotation.logo_recognition_annotations = []

        mock_operation = MagicMock()
        mock_operation.result.return_value = MagicMock()
        mock_operation.result.return_value.annotation_results = [annotation]

        with patch(
            "backend.trend_intelligence.analyzers.video_intelligence_analyzer.videointelligence"
        ) as mock_vi:
            mock_client = MagicMock()
            mock_client.annotate_video.return_value = mock_operation
            mock_vi.VideoIntelligenceServiceClient.return_value = mock_client
            mock_vi.Feature = MagicMock()
            mock_vi.AnnotateVideoRequest = dict

            result = await analyze_video(str(video_file))

        assert result["shots"] == []
        assert result["labels"] == []
        assert result["text"] == []
        assert result["objects"] == []
        assert result["logos"] == []
