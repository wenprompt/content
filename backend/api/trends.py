"""Trend Intelligence API endpoints."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import get_settings
from backend.database import get_db
from backend.models import Project, Shot, TrendAnalysis
from backend.pipeline.prompt_generator import generate_tool_prompt
from backend.schemas import (
    TrendAnalysisResponse,
    TrendAnalyzeRequest,
    TrendFetchRequest,
    TrendRemixRequest,
)
from backend.trend_intelligence.analyzers.gemini_analyzer import analyze_video as gemini_analyze
from backend.trend_intelligence.analyzers.gemini_analyzer import download_video
from backend.trend_intelligence.prompt_enhancer import (
    create_shot_plans_from_analysis,
    generate_prompts,
)

router = APIRouter(prefix="/api/trends", tags=["trends"])

DB = Annotated[AsyncSession, Depends(get_db)]


def _get_fetcher(platform: str) -> Any:
    """Return the appropriate fetcher for the platform."""
    settings = get_settings()
    if not settings.apify_api_token:
        raise HTTPException(status_code=400, detail="APIFY_API_TOKEN not configured")

    if platform == "tiktok":
        from backend.trend_intelligence.fetchers.tiktok_fetcher import TikTokFetcher

        return TikTokFetcher(api_token=settings.apify_api_token)
    elif platform == "instagram":
        from backend.trend_intelligence.fetchers.instagram_fetcher import InstagramFetcher

        return InstagramFetcher(api_token=settings.apify_api_token)
    elif platform == "facebook":
        from backend.trend_intelligence.fetchers.facebook_fetcher import FacebookFetcher

        return FacebookFetcher(api_token=settings.apify_api_token)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")


@router.post("/fetch")
async def fetch_trends(data: TrendFetchRequest) -> list[dict[str, Any]]:
    """Run Apify fetcher for platform, return video metadata list."""
    fetcher = _get_fetcher(data.platform)
    results: list[dict[str, Any]] = await fetcher.fetch(
        niche=data.niche,
        region=data.region,
        time_range=data.time_range,
        min_views=data.min_views,
        max_results=data.max_results,
        hashtags=data.hashtags,
    )
    return results


@router.post("/analyze", response_model=TrendAnalysisResponse)
async def analyze_trend(data: TrendAnalyzeRequest, db: DB) -> TrendAnalysis:
    """Download video, run Gemini + Video Intelligence in parallel, store result."""
    settings = get_settings()

    if not settings.gemini_api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured")

    # Download video to temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = await download_video(data.video_url, Path(tmpdir))
        video_path_str = str(video_path)

        # Run both analyzers in parallel
        tasks: list[asyncio.Task[dict[str, Any]]] = [
            asyncio.create_task(
                gemini_analyze(
                    video_path_str,
                    api_key=settings.gemini_api_key,
                    model=settings.trend_analysis_model,
                )
            ),
        ]

        # Only run Video Intelligence if credentials are configured
        vi_result: dict[str, Any] = {}
        if settings.google_application_credentials:
            from backend.trend_intelligence.analyzers.video_intelligence_analyzer import (
                analyze_video as vi_analyze,
            )

            tasks.append(asyncio.create_task(vi_analyze(video_path_str)))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        gemini_result = results[0] if not isinstance(results[0], BaseException) else {}
        if isinstance(results[0], BaseException):
            raise HTTPException(
                status_code=500,
                detail=f"Gemini analysis failed: {results[0]}",
            )

        if len(results) > 1 and not isinstance(results[1], BaseException):
            vi_result = results[1]

    # Store analysis
    analysis = TrendAnalysis(
        platform=data.platform,
        niche=data.niche,
        video_url=data.video_url,
        video_id="",
        gemini_analysis=json.dumps(gemini_result),
        video_intelligence=json.dumps(vi_result),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    return analysis


@router.post("/remix")
async def remix_trend(data: TrendRemixRequest, db: DB) -> dict[str, Any]:
    """Read stored analysis, create shot plans, add Shot records to project."""
    # Load trend analysis
    analysis_result = await db.execute(
        select(TrendAnalysis).where(TrendAnalysis.id == data.trend_analysis_id)
    )
    analysis_row = analysis_result.scalar_one_or_none()
    if not analysis_row:
        raise HTTPException(status_code=404, detail="Trend analysis not found")

    # Load project with shots
    project_result = await db.execute(
        select(Project)
        .where(Project.id == data.project_id)
        .options(selectinload(Project.shots))
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Parse the Gemini analysis
    gemini_analysis: dict[str, Any] = json.loads(analysis_row.gemini_analysis or "{}")
    if not gemini_analysis:
        raise HTTPException(status_code=400, detail="No Gemini analysis available for this trend")

    # Create shot plans from analysis
    shot_plans = create_shot_plans_from_analysis(gemini_analysis, project)
    shot_plans = generate_prompts(shot_plans, project)

    # Delete existing shots
    for existing_shot in list(project.shots):
        await db.delete(existing_shot)

    # Create Shot records from plans
    shots_created: list[dict[str, Any]] = []
    for plan in shot_plans:
        tool_prompt = generate_tool_prompt(plan, project)

        shot = Shot(
            project_id=project.id,
            order_index=plan.order_index,
            name=plan.name,
            shot_type=plan.shot_type,
            tool=plan.tool,
            prompt=tool_prompt.prompt,
            negative_prompt=tool_prompt.negative_prompt,
            duration=plan.duration,
            width=plan.width,
            height=plan.height,
            lora_name=tool_prompt.lora_name,
            lora_strength=tool_prompt.lora_strength,
            transition_type=plan.transition_type,
        )
        db.add(shot)
        shots_created.append({
            "name": plan.name,
            "tool": plan.tool,
            "duration": plan.duration,
            "camera_movement": plan.camera_movement,
            "lora_name": tool_prompt.lora_name,
        })

    # Update project status
    project.status = "planned"
    await db.commit()

    return {
        "project_id": project.id,
        "trend_analysis_id": analysis_row.id,
        "shots_created": len(shots_created),
        "shots": shots_created,
        "status": "planned",
    }


@router.get("/analyses", response_model=list[TrendAnalysisResponse])
async def list_analyses(db: DB) -> list[TrendAnalysis]:
    """List all stored trend analyses."""
    result = await db.execute(
        select(TrendAnalysis).order_by(TrendAnalysis.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/analyses/{analysis_id}", response_model=TrendAnalysisResponse)
async def get_analysis(analysis_id: str, db: DB) -> TrendAnalysis:
    """Get a single trend analysis by ID."""
    result = await db.execute(
        select(TrendAnalysis).where(TrendAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Trend analysis not found")
    return analysis
