"""End-to-end trend intelligence test: YouTube URL → download → Gemini analysis → shot plans.

Run with:
    uv run pytest tests/test_e2e_trend.py -m integration -v -s
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from backend.config import get_settings
from backend.models import Project  # noqa: F811

_settings = get_settings()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _settings.gemini_api_key, reason="GEMINI_API_KEY not set"),
]


class TestE2ETrend:
    async def test_youtube_to_shot_plans(self) -> None:
        """Full flow: download YouTube video → Gemini analysis → shot plans."""
        from backend.trend_intelligence.analyzers.gemini_analyzer import (
            analyze_video,
            download_video,
        )
        from backend.trend_intelligence.prompt_enhancer import create_shot_plans_from_analysis

        url = "https://www.youtube.com/watch?v=ojGj7Hpa-OQ"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            # Step 1: Download
            print("\n--- Step 1: Downloading video ---")
            video_path = await download_video(url, tmp_path)
            assert video_path.exists()
            size_mb = video_path.stat().st_size / 1024 / 1024
            print(f"Downloaded: {video_path.name} ({size_mb:.1f} MB)")
            assert size_mb > 0.1, "Video file too small — download may have failed"

            # Step 2: Gemini Analysis
            print("\n--- Step 2: Analyzing with Gemini ---")
            analysis = await analyze_video(
                str(video_path),
                api_key=_settings.gemini_api_key,
                model=_settings.trend_analysis_model,
            )
            print(json.dumps(analysis, indent=2))

            # Verify all 8 dimensions
            assert "hook_analysis" in analysis
            assert "visual_style" in analysis
            assert "camera_work" in analysis
            assert "pacing" in analysis
            assert "audio" in analysis
            assert "content_structure" in analysis
            assert "product_presentation" in analysis
            assert "engagement_drivers" in analysis
            assert "shot_breakdown" in analysis
            assert len(analysis["shot_breakdown"]) > 0

            # Step 3: Create shot plans
            print("\n--- Step 3: Creating shot plans ---")
            project = Project(
                name="E2E Test",
                target_platform="tiktok",
                description="test product description",
            )

            plans = create_shot_plans_from_analysis(analysis, project)
            assert len(plans) > 0

            for p in plans:
                print(
                    f"  {p.name}: {p.camera_movement} ({p.duration}s) "
                    f"- {p.description[:80]}"
                )
                assert p.tool == "ltx"
                assert 2.0 <= p.duration <= 20.0
                assert p.camera_movement

            print(f"\nTotal shots: {len(plans)}")
            print("E2E test PASSED")
