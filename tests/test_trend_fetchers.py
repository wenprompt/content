"""Tests for trend intelligence fetchers (TikTok, Instagram, Facebook)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# TikTok Fetcher
# ---------------------------------------------------------------------------


class TestTikTokFetcher:
    def _make_raw_item(self, **overrides: Any) -> dict[str, Any]:
        defaults: dict[str, Any] = {
            "id": "123456",
            "webVideoUrl": "https://tiktok.com/@user/video/123456",
            "videoUrl": "https://cdn.tiktok.com/video.mp4",
            "text": "Amazing product demo #viral",
            "playCount": 500_000,
            "diggCount": 50_000,
            "commentCount": 1_000,
            "shareCount": 5_000,
            "videoMeta": {"duration": 15},
            "authorMeta": {
                "name": "creator1",
                "fans": 100_000,
            },
            "hashtags": [{"name": "viral"}, {"name": "fyp"}],
            "musicMeta": {"musicName": "Original Sound"},
        }
        defaults.update(overrides)
        return defaults

    async def test_normalize_extracts_fields(self) -> None:
        from backend.trend_intelligence.fetchers.tiktok_fetcher import TikTokFetcher

        raw = self._make_raw_item()
        result = TikTokFetcher._normalize(raw)

        assert result["video_id"] == "123456"
        assert result["video_url"] == "https://tiktok.com/@user/video/123456"
        assert result["download_url"] == "https://cdn.tiktok.com/video.mp4"
        assert result["view_count"] == 500_000
        assert result["like_count"] == 50_000
        assert result["comment_count"] == 1_000
        assert result["share_count"] == 5_000
        assert result["duration"] == 15
        assert result["creator_name"] == "creator1"
        assert result["creator_followers"] == 100_000
        assert result["hashtags"] == ["viral", "fyp"]
        assert result["music_name"] == "Original Sound"

    async def test_fetch_filters_by_min_views(self) -> None:
        from backend.trend_intelligence.fetchers.tiktok_fetcher import TikTokFetcher

        items = [
            self._make_raw_item(id="1", playCount=50_000),
            self._make_raw_item(id="2", playCount=200_000),
            self._make_raw_item(id="3", playCount=1_000_000),
        ]

        mock_dataset = MagicMock()

        async def mock_iterate() -> Any:
            for item in items:
                yield item

        mock_dataset.iterate_items = mock_iterate

        mock_actor = MagicMock()
        mock_actor.call = AsyncMock(return_value={"defaultDatasetId": "ds-123"})

        with patch("backend.trend_intelligence.fetchers.tiktok_fetcher.ApifyClientAsync") as mock_cls:  # noqa: E501
            mock_client = MagicMock()
            mock_client.actor.return_value = mock_actor
            mock_client.dataset.return_value = mock_dataset
            mock_cls.return_value = mock_client

            fetcher = TikTokFetcher(api_token="test-token")
            results = await fetcher.fetch(niche="tech", min_views=100_000)

        assert len(results) == 2
        assert results[0]["view_count"] == 1_000_000  # sorted desc
        assert results[1]["view_count"] == 200_000

    async def test_fetch_empty_results(self) -> None:
        from backend.trend_intelligence.fetchers.tiktok_fetcher import TikTokFetcher

        mock_actor = MagicMock()
        mock_actor.call = AsyncMock(return_value=None)

        with patch("backend.trend_intelligence.fetchers.tiktok_fetcher.ApifyClientAsync") as mock_cls:  # noqa: E501
            mock_client = MagicMock()
            mock_client.actor.return_value = mock_actor
            mock_cls.return_value = mock_client

            fetcher = TikTokFetcher(api_token="test-token")
            results = await fetcher.fetch(niche="tech")

        assert results == []

    async def test_fetch_no_dataset_id(self) -> None:
        from backend.trend_intelligence.fetchers.tiktok_fetcher import TikTokFetcher

        mock_actor = MagicMock()
        mock_actor.call = AsyncMock(return_value={"defaultDatasetId": ""})

        with patch("backend.trend_intelligence.fetchers.tiktok_fetcher.ApifyClientAsync") as mock_cls:  # noqa: E501
            mock_client = MagicMock()
            mock_client.actor.return_value = mock_actor
            mock_cls.return_value = mock_client

            fetcher = TikTokFetcher(api_token="test-token")
            results = await fetcher.fetch(niche="tech")

        assert results == []

    async def test_fetch_respects_max_results(self) -> None:
        from backend.trend_intelligence.fetchers.tiktok_fetcher import TikTokFetcher

        items = [
            self._make_raw_item(id=str(i), playCount=500_000 + i)
            for i in range(10)
        ]

        mock_dataset = MagicMock()

        async def mock_iterate() -> Any:
            for item in items:
                yield item

        mock_dataset.iterate_items = mock_iterate
        mock_actor = MagicMock()
        mock_actor.call = AsyncMock(return_value={"defaultDatasetId": "ds-123"})

        with patch("backend.trend_intelligence.fetchers.tiktok_fetcher.ApifyClientAsync") as mock_cls:  # noqa: E501
            mock_client = MagicMock()
            mock_client.actor.return_value = mock_actor
            mock_client.dataset.return_value = mock_dataset
            mock_cls.return_value = mock_client

            fetcher = TikTokFetcher(api_token="test-token")
            results = await fetcher.fetch(niche="tech", max_results=3)

        assert len(results) == 3


# ---------------------------------------------------------------------------
# Instagram Fetcher
# ---------------------------------------------------------------------------


class TestInstagramFetcher:
    async def test_normalize_extracts_fields(self) -> None:
        from backend.trend_intelligence.fetchers.instagram_fetcher import InstagramFetcher

        raw = {
            "id": "ig-789",
            "url": "https://instagram.com/reel/xyz",
            "videoUrl": "https://cdn.instagram.com/video.mp4",
            "caption": "Check this out!",
            "videoViewCount": 300_000,
            "likesCount": 20_000,
            "commentsCount": 500,
            "sharesCount": 100,
            "videoDuration": 30,
            "ownerUsername": "igcreator",
            "ownerFollowerCount": 50_000,
            "hashtags": ["trending", "reels"],
            "type": "Video",
        }
        result = InstagramFetcher._normalize(raw)

        assert result["video_id"] == "ig-789"
        assert result["view_count"] == 300_000
        assert result["creator_name"] == "igcreator"
        assert result["hashtags"] == ["trending", "reels"]


# ---------------------------------------------------------------------------
# Facebook Fetcher
# ---------------------------------------------------------------------------


class TestFacebookFetcher:
    async def test_normalize_extracts_fields(self) -> None:
        from backend.trend_intelligence.fetchers.facebook_fetcher import FacebookFetcher

        raw = {
            "postId": "fb-456",
            "postUrl": "https://facebook.com/reel/456",
            "videoUrl": "https://cdn.facebook.com/video.mp4",
            "text": "Amazing content",
            "viewCount": 1_000_000,
            "likesCount": 80_000,
            "commentsCount": 2_000,
            "sharesCount": 10_000,
            "videoDuration": 60,
            "userName": "fbcreator",
            "followerCount": 200_000,
            "hashtags": ["viral"],
        }
        result = FacebookFetcher._normalize(raw)

        assert result["video_id"] == "fb-456"
        assert result["view_count"] == 1_000_000
        assert result["creator_name"] == "fbcreator"
