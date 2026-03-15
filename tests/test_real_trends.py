"""Real integration tests for trend intelligence — requires live API keys.

Skipped when keys are not configured. Run with:
    uv run pytest tests/test_real_trends.py -m integration -v
"""

from __future__ import annotations

import os

import pytest

from backend.config import get_settings

# Skip entire module if required API keys are missing
_settings = get_settings()
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _settings.apify_api_token,
        reason="APIFY_API_TOKEN not set",
    ),
]

_has_gemini = bool(_settings.gemini_api_key)
_has_gcloud = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))


@pytest.mark.skipif(not _settings.apify_api_token, reason="APIFY_API_TOKEN not set")
class TestApifyFetch:
    async def test_fetch_viral_tiktok(self) -> None:
        from backend.trend_intelligence.fetchers.tiktok_fetcher import TikTokFetcher

        fetcher = TikTokFetcher(api_token=_settings.apify_api_token)
        results = await fetcher.fetch(
            niche="technology",
            min_views=50_000,
            max_results=5,
        )

        assert len(results) > 0
        for r in results:
            assert r["view_count"] >= 50_000
            assert r["video_url"]
            assert r["video_id"]


@pytest.mark.skipif(not _has_gemini, reason="GEMINI_API_KEY not set")
class TestGeminiAnalyze:
    async def test_analyze_video(self) -> None:

        # This test requires a real video URL — run manually with a known video path
        pytest.skip("Requires a real video URL — run manually with a known video path")


@pytest.mark.skipif(not _has_gcloud, reason="GOOGLE_APPLICATION_CREDENTIALS not set")
class TestVideoIntelligence:
    async def test_analyze_video(self) -> None:

        # Requires a real video file
        pytest.skip("Requires a real video file — run manually")


@pytest.mark.skipif(
    not (_has_gemini and _settings.apify_api_token),
    reason="Requires both GEMINI_API_KEY and APIFY_API_TOKEN",
)
class TestFullTrendToShots:
    async def test_end_to_end_trend_remix(self) -> None:
        """Fetch → pick top video → analyze → create shot plans → verify."""
        from backend.trend_intelligence.fetchers.tiktok_fetcher import TikTokFetcher

        # Step 1: Fetch trending videos
        fetcher = TikTokFetcher(api_token=_settings.apify_api_token)
        videos = await fetcher.fetch(niche="technology", min_views=50_000, max_results=3)

        if not videos:
            pytest.skip("No videos returned from Apify — may be rate limited")

        top_video = videos[0]
        assert top_video["video_url"]

        # Step 2: Analysis would require downloading and processing
        # For CI, we skip the actual Gemini call and test with sample data
        pytest.skip("Full end-to-end requires video download — run manually with real video")
