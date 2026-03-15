"""Fetch trending TikTok videos via Apify scraper."""

from __future__ import annotations

from typing import Any

from apify_client import ApifyClientAsync


class TikTokFetcher:
    """Fetches trending TikTok videos using Apify's TikTok scraper actor."""

    ACTOR_ID = "clockworks/tiktok-scraper"

    def __init__(self, api_token: str) -> None:
        self.api_token = api_token

    async def fetch(
        self,
        niche: str = "",
        region: str = "us",
        time_range: str = "7d",
        min_views: int = 100_000,
        max_results: int = 50,
        hashtags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch trending TikTok videos and return normalized metadata."""
        client = ApifyClientAsync(token=self.api_token)

        search_queries: list[str] = []
        if niche:
            search_queries.append(niche)
        if hashtags:
            search_queries.extend(f"#{tag}" for tag in hashtags)

        run_input: dict[str, Any] = {
            "searchQueries": search_queries or ["trending"],
            "resultsPerPage": max_results * 2,  # over-fetch to allow post-filter
            "shouldDownloadVideos": False,
        }

        run = await client.actor(self.ACTOR_ID).call(run_input=run_input)
        if not run:
            return []

        dataset_id = run.get("defaultDatasetId", "")
        if not dataset_id:
            return []

        items: list[dict[str, Any]] = []
        async for item in client.dataset(dataset_id).iterate_items():
            items.append(item)

        results = [self._normalize(item) for item in items]

        # Post-filter by min_views
        results = [r for r in results if r["view_count"] >= min_views]

        # Sort by views descending
        results.sort(key=lambda x: x["view_count"], reverse=True)

        return results[:max_results]

    @staticmethod
    def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
        # clockworks/tiktok-scraper puts stats at top level AND in videoMeta
        video_meta = raw.get("videoMeta", {})
        author = raw.get("authorMeta", raw.get("author", {}))

        return {
            "video_id": str(raw.get("id", "")),
            "video_url": str(raw.get("webVideoUrl", raw.get("url", ""))),
            "download_url": str(
                raw.get("videoUrl", raw.get("downloadUrl", ""))
            ),
            "description": str(raw.get("text", raw.get("description", ""))),
            "view_count": int(
                raw.get("playCount", video_meta.get("playCount", 0))
            ),
            "like_count": int(
                raw.get("diggCount", video_meta.get("diggCount", 0))
            ),
            "comment_count": int(
                raw.get("commentCount", video_meta.get("commentCount", 0))
            ),
            "share_count": int(
                raw.get("shareCount", video_meta.get("shareCount", 0))
            ),
            "duration": int(
                video_meta.get("duration", raw.get("duration", 0))
            ),
            "creator_name": str(
                author.get("name", author.get("nickName", ""))
            ),
            "creator_followers": int(
                author.get("fans", author.get("followerCount", 0))
            ),
            "hashtags": [
                str(h.get("name", h))
                for h in raw.get("hashtags", raw.get("challenges", []))
            ],
            "music_name": str(
                raw.get("musicMeta", {}).get("musicName", "")
            ),
        }
