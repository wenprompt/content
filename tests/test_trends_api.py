"""Integration tests for the trends API endpoints."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from backend.models import Project, Shot, TrendAnalysis
from tests.conftest import db_session

if TYPE_CHECKING:
    from httpx import AsyncClient

SAMPLE_GEMINI_ANALYSIS: dict[str, Any] = {
    "hook_analysis": {"visual_element": "close-up", "camera_angle": "low", "timing_seconds": 1.5},
    "visual_style": {
        "color_palette": ["#FF5733"],
        "lighting": "warm golden",
        "aesthetic": "minimal",
    },
    "camera_work": {
        "shot_types": ["close-up"],
        "movements": ["dolly_in"],
        "transitions": ["cut"],
        "avg_shot_duration": 3.0,
    },
    "pacing": {
        "tempo": "fast", "energy_curve": "builds", "number_of_cuts": 3, "total_duration": 10.0,
    },
    "audio": {
        "music_genre": "electronic",
        "music_tempo_bpm": 128,
        "sound_effects": [],
        "audio_visual_sync": "tight",
    },
    "content_structure": {"pattern": "hook-setup-payoff", "format_type": "showcase"},
    "product_presentation": {"appearance_method": "reveal", "features_highlighted": ["design"]},
    "engagement_drivers": {
        "shareability_factor": "satisfying",
        "emotional_trigger": "curiosity",
        "cta": "",
    },
    "shot_breakdown": [
        {
            "timestamp": "0:00-0:03",
            "description": "Hook close-up",
            "camera_movement": "dolly_in",
            "duration_sec": 3.0,
        },
        {
            "timestamp": "0:03-0:07",
            "description": "Product reveal",
            "camera_movement": "static",
            "duration_sec": 4.0,
        },
    ],
}


class TestTrendsFetch:
    async def test_fetch_returns_videos(self, client: AsyncClient) -> None:
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(
            return_value=[
                {"video_id": "1", "video_url": "https://example.com/1", "view_count": 500_000},
                {"video_id": "2", "video_url": "https://example.com/2", "view_count": 200_000},
            ]
        )

        with patch("backend.api.trends._get_fetcher", return_value=mock_fetcher):
            r = await client.post(
                "/api/trends/fetch",
                json={"platform": "tiktok", "niche": "tech", "min_views": 100000},
            )

        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        assert data[0]["video_id"] == "1"

    async def test_fetch_empty(self, client: AsyncClient) -> None:
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=[])

        with patch("backend.api.trends._get_fetcher", return_value=mock_fetcher):
            r = await client.post(
                "/api/trends/fetch",
                json={"platform": "tiktok", "niche": "nonexistent"},
            )

        assert r.status_code == 200
        assert r.json() == []


class TestTrendsAnalyze:
    async def test_analyze_stores_result(self, client: AsyncClient) -> None:
        mock_path = MagicMock()
        mock_path.__str__ = lambda self: "/tmp/video.mp4"

        with (
            patch("backend.api.trends.get_settings") as mock_settings,
            patch(
                "backend.api.trends.download_video",
                new_callable=AsyncMock, return_value=mock_path,
            ),
            patch(
                "backend.api.trends.gemini_analyze",
                new_callable=AsyncMock, return_value=SAMPLE_GEMINI_ANALYSIS,
            ),
        ):
            settings = MagicMock()
            settings.gemini_api_key = "test-key"
            settings.trend_analysis_model = "gemini-3-pro"
            settings.google_application_credentials = ""
            mock_settings.return_value = settings

            r = await client.post(
                "/api/trends/analyze",
                json={
                    "video_url": "https://example.com/video.mp4",
                    "platform": "tiktok",
                    "niche": "tech",
                },
            )

        assert r.status_code == 200
        data = r.json()
        assert data["platform"] == "tiktok"
        assert data["niche"] == "tech"
        assert data["id"]
        # Gemini analysis should be stored as JSON string
        stored = json.loads(data["gemini_analysis"])
        assert stored["pacing"]["tempo"] == "fast"

    async def test_analyze_no_api_key(self, client: AsyncClient) -> None:
        with patch("backend.api.trends.get_settings") as mock_settings:
            settings = MagicMock()
            settings.gemini_api_key = ""
            mock_settings.return_value = settings

            r = await client.post(
                "/api/trends/analyze",
                json={"video_url": "https://example.com/video.mp4"},
            )

        assert r.status_code == 400
        assert "GEMINI_API_KEY" in r.json()["detail"]


class TestTrendsRemix:
    async def _setup_analysis_and_project(self) -> tuple[str, str]:
        """Create a TrendAnalysis and a Project in the test DB, return their IDs."""
        async with db_session() as session:
            analysis = TrendAnalysis(
                platform="tiktok",
                niche="tech",
                video_url="https://example.com/video.mp4",
                gemini_analysis=json.dumps(SAMPLE_GEMINI_ANALYSIS),
            )
            session.add(analysis)

            project = Project(
                name="Remix Test",
                description="Test project for remixing",
                content_type="product_ad",
                target_platform="tiktok",
                style_mood="cinematic",
                key_message="Buy this",
            )
            session.add(project)
            await session.commit()

            return analysis.id, project.id

    async def test_remix_creates_shots(self, client: AsyncClient) -> None:
        analysis_id, project_id = await self._setup_analysis_and_project()

        r = await client.post(
            "/api/trends/remix",
            json={"trend_analysis_id": analysis_id, "project_id": project_id},
        )

        assert r.status_code == 200
        data = r.json()
        assert data["shots_created"] == 2
        assert data["status"] == "planned"
        assert data["project_id"] == project_id

        # Verify shots have correct fields
        for shot in data["shots"]:
            assert shot["tool"] in ("veo", "sora", "ltx")
            assert shot["duration"] > 0

    async def test_remix_sets_project_planned(self, client: AsyncClient) -> None:
        analysis_id, project_id = await self._setup_analysis_and_project()

        await client.post(
            "/api/trends/remix",
            json={"trend_analysis_id": analysis_id, "project_id": project_id},
        )

        # Check project status in DB
        async with db_session() as session:
            result = await session.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one()
            assert project.status == "planned"

    async def test_remix_creates_shot_records(self, client: AsyncClient) -> None:
        analysis_id, project_id = await self._setup_analysis_and_project()

        await client.post(
            "/api/trends/remix",
            json={"trend_analysis_id": analysis_id, "project_id": project_id},
        )

        # Verify Shot records in DB
        async with db_session() as session:
            result = await session.execute(
                select(Shot).where(Shot.project_id == project_id).order_by(Shot.order_index)
            )
            shots = list(result.scalars().all())

        assert len(shots) == 2
        assert shots[0].tool in ("veo", "sora", "ltx")
        assert shots[0].prompt  # Should have a generated prompt

    async def test_remix_analysis_not_found(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/trends/remix",
            json={"trend_analysis_id": "nonexistent", "project_id": "nonexistent"},
        )
        assert r.status_code == 404

    async def test_remix_project_not_found(self, client: AsyncClient) -> None:
        async with db_session() as session:
            analysis = TrendAnalysis(
                platform="tiktok",
                niche="tech",
                video_url="https://example.com/video.mp4",
                gemini_analysis=json.dumps(SAMPLE_GEMINI_ANALYSIS),
            )
            session.add(analysis)
            await session.commit()
            analysis_id = analysis.id

        r = await client.post(
            "/api/trends/remix",
            json={"trend_analysis_id": analysis_id, "project_id": "nonexistent"},
        )
        assert r.status_code == 404


class TestTrendsAnalysesList:
    async def test_list_empty(self, client: AsyncClient) -> None:
        r = await client.get("/api/trends/analyses")
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_returns_analyses(self, client: AsyncClient) -> None:
        async with db_session() as session:
            session.add(TrendAnalysis(platform="tiktok", niche="tech", video_url="https://a.com"))
            session.add(TrendAnalysis(platform="instagram", niche="food", video_url="https://b.com"))
            await session.commit()

        r = await client.get("/api/trends/analyses")
        assert r.status_code == 200
        assert len(r.json()) == 2

    async def test_get_single_analysis(self, client: AsyncClient) -> None:
        async with db_session() as session:
            analysis = TrendAnalysis(
                platform="tiktok", niche="tech", video_url="https://a.com"
            )
            session.add(analysis)
            await session.commit()
            aid = analysis.id

        r = await client.get(f"/api/trends/analyses/{aid}")
        assert r.status_code == 200
        assert r.json()["platform"] == "tiktok"

    async def test_get_analysis_not_found(self, client: AsyncClient) -> None:
        r = await client.get("/api/trends/analyses/nonexistent")
        assert r.status_code == 404
