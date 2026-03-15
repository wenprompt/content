"""Fetch trending Instagram Reels via Apify scraper."""

from __future__ import annotations

from typing import Any

from apify_client import ApifyClientAsync


class InstagramFetcher:
    """Fetches trending Instagram Reels using Apify's Instagram scraper actor."""

    ACTOR_ID = "apify/instagram-scraper"

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
        """Fetch trending Instagram Reels and return normalized metadata."""
        client = ApifyClientAsync(token=self.api_token)

        search_queries: list[str] = []
        if hashtags:
            search_queries.extend(hashtags)
        elif niche:
            search_queries.append(niche)

        run_input: dict[str, Any] = {
            "search": niche or "trending",
            "searchType": "hashtag" if hashtags else "user",
            "resultsType": "posts",
            "resultsLimit": max_results * 2,
        }

        run = await client.actor(self.ACTOR_ID).call(run_input=run_input)
        if not run:
            return []

        dataset_id = run.get("defaultDatasetId", "")
        if not dataset_id:
            return []

        items: list[dict[str, Any]] = []
        async for item in client.dataset(dataset_id).iterate_items():
            # Only include video/reel posts
            if item.get("type") in ("Video", "Reel", "video"):
                items.append(item)

        results = [self._normalize(item) for item in items]
        results = [r for r in results if r["view_count"] >= min_views]
        results.sort(key=lambda x: x["view_count"], reverse=True)

        return results[:max_results]

    @staticmethod
    def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "video_id": str(raw.get("id", raw.get("shortCode", ""))),
            "video_url": str(raw.get("url", "")),
            "download_url": str(raw.get("videoUrl", "")),
            "description": str(raw.get("caption", "")),
            "view_count": int(raw.get("videoViewCount", raw.get("viewCount", 0))),
            "like_count": int(raw.get("likesCount", 0)),
            "comment_count": int(raw.get("commentsCount", 0)),
            "share_count": int(raw.get("sharesCount", 0)),
            "duration": int(raw.get("videoDuration", 0)),
            "creator_name": str(raw.get("ownerUsername", "")),
            "creator_followers": int(raw.get("ownerFollowerCount", 0)),
            "hashtags": [str(h) for h in raw.get("hashtags", [])],
            "music_name": str(raw.get("musicInfo", {}).get("title", "")),
        }
