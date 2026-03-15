"""Fetch trending Facebook Reels via Apify scraper."""

from __future__ import annotations

from typing import Any

from apify_client import ApifyClientAsync


class FacebookFetcher:
    """Fetches trending Facebook Reels using Apify's Facebook scraper actor."""

    ACTOR_ID = "apify/facebook-scraper"

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
        """Fetch trending Facebook Reels and return normalized metadata."""
        client = ApifyClientAsync(token=self.api_token)

        run_input: dict[str, Any] = {
            "searchQuery": niche or "trending",
            "maxResults": max_results * 2,
            "contentType": "reels",
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
        results = [r for r in results if r["view_count"] >= min_views]
        results.sort(key=lambda x: x["view_count"], reverse=True)

        return results[:max_results]

    @staticmethod
    def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "video_id": str(raw.get("postId", raw.get("id", ""))),
            "video_url": str(raw.get("postUrl", raw.get("url", ""))),
            "download_url": str(raw.get("videoUrl", "")),
            "description": str(raw.get("text", raw.get("description", ""))),
            "view_count": int(raw.get("viewCount", raw.get("views", 0))),
            "like_count": int(raw.get("likesCount", raw.get("likes", 0))),
            "comment_count": int(raw.get("commentsCount", raw.get("comments", 0))),
            "share_count": int(raw.get("sharesCount", raw.get("shares", 0))),
            "duration": int(raw.get("videoDuration", 0)),
            "creator_name": str(raw.get("userName", raw.get("pageName", ""))),
            "creator_followers": int(raw.get("followerCount", 0)),
            "hashtags": [str(h) for h in raw.get("hashtags", [])],
            "music_name": str(raw.get("musicInfo", {}).get("title", "")),
        }
