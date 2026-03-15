"""Scrape viral TikTok → analyze → recreate as animation via LTX 2.3.

Saves the original video to downloads/ for side-by-side comparison.

Usage:
    uv run python -m scripts.tiktok_remix --niche "satisfying" --style "3D Pixar animation"
    uv run python -m scripts.tiktok_remix --url "https://tiktok.com/@user/video/123"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser(description="TikTok viral video → animation remix")
    parser.add_argument("--url", help="Direct TikTok URL (skip scraping)")
    parser.add_argument("--niche", default="satisfying", help="Search niche for scraper")
    parser.add_argument("--min-views", type=int, default=1_000_000, help="Minimum view count")
    parser.add_argument("--pick", type=int, default=1, help="Which result to pick (1-indexed)")
    parser.add_argument("--style", default="3D Pixar cartoon animation", help="Animation style")
    parser.add_argument(
        "--character",
        default="A cute 3D animated cartoon character with big eyes and round face",
        help="Character description",
    )
    parser.add_argument("--max-shots", type=int, default=8, help="Max shots to generate")
    parser.add_argument(
        "--story",
        help="Your description of what actually happens in the video. "
        "Supplements Gemini's analysis so the AI understands the essence/narrative.",
    )
    parser.add_argument(
        "--tool",
        choices=["auto", "ltx", "veo", "sora"],
        default="auto",
        help="Video generation tool (default: auto, routes per-shot to veo/sora)",
    )
    parser.add_argument("--generate", action="store_true", help="Auto-start video generation")
    args = parser.parse_args()

    from backend.config import get_settings
    from backend.database import async_session, init_db
    from backend.models import Project, Shot
    from backend.pipeline.prompt_generator import generate_tool_prompt
    from backend.trend_intelligence.analyzers.gemini_analyzer import (
        analyze_video,
        download_video,
    )
    from backend.trend_intelligence.prompt_enhancer import (
        adapt_analysis_for_product,
        adapt_analysis_with_story,
        create_shot_plans_from_analysis,
    )

    settings = get_settings()
    if not settings.gemini_api_key:
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    # --- Step 1: Find a viral TikTok ---
    video_url = args.url
    video_meta: dict[str, object] = {}

    if not video_url:
        if not settings.apify_api_token:
            print("ERROR: APIFY_API_TOKEN not set — use --url to provide a direct link")
            sys.exit(1)

        from backend.trend_intelligence.fetchers.tiktok_fetcher import TikTokFetcher

        print(f"\n=== Step 1: Scraping TikTok for '{args.niche}' (min {args.min_views:,} views) ===")
        fetcher = TikTokFetcher(api_token=settings.apify_api_token)
        results = await fetcher.fetch(
            niche=args.niche,
            min_views=args.min_views,
            max_results=10,
        )

        if not results:
            print("No videos found matching criteria")
            sys.exit(1)

        print(f"Found {len(results)} videos:")
        for i, r in enumerate(results):
            desc = r["description"][:70].encode("ascii", "replace").decode()
            print(f"  {i + 1}. {r['view_count']:>12,} views | {r['duration']:>3}s | {desc}")

        pick_idx = min(args.pick - 1, len(results) - 1)
        video_meta = results[pick_idx]
        video_url = str(video_meta["video_url"])
        print(f"\nPicked #{pick_idx + 1}: {video_url}")
    else:
        print(f"\n=== Step 1: Using provided URL ===\n{video_url}")

    # --- Step 2: Download & save original ---
    print("\n=== Step 2: Downloading original video ===")
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)

    video_path = await download_video(video_url, downloads_dir)
    size_mb = video_path.stat().st_size / 1024 / 1024
    print(f"Saved original: {video_path} ({size_mb:.1f} MB)")

    # --- Step 3: Gemini analysis ---
    print("\n=== Step 3: Analyzing with Gemini ===")
    analysis = await analyze_video(
        str(video_path),
        api_key=settings.gemini_api_key,
        model=settings.trend_analysis_model,
    )

    shots = analysis.get("shot_breakdown", [])
    print(f"Detected {len(shots)} shots")
    print(f"Style: {analysis.get('visual_style', {}).get('aesthetic', 'N/A')}")
    print(f"Pacing: {analysis.get('pacing', {}).get('tempo', 'N/A')}")
    for i, s in enumerate(shots):
        desc = str(s.get("description", ""))[:70]
        print(f"  {i + 1}. [{s.get('camera_movement', '?')}] {s.get('duration_sec', 0)}s - {desc}")

    # Trim to max shots if needed
    if len(shots) > args.max_shots:
        print(f"\nTrimming from {len(shots)} to {args.max_shots} shots")
        analysis["shot_breakdown"] = shots[: args.max_shots]

    # --- Step 4: Adapt for animation ---
    print(f"\n=== Step 4: Adapting as '{args.style}' ===")
    if args.story:
        print(f"Using story: {args.story[:80]}...")
        adapted = await adapt_analysis_with_story(
            analysis=analysis,
            story=args.story,
            style=args.style,
            character_description=args.character,
            api_key=settings.gemini_api_key,
            model=settings.trend_analysis_model,
        )
    else:
        adapted = await adapt_analysis_for_product(
            analysis=analysis,
            product_name=args.style,
            product_description=(
                f"{args.character}. "
                f"Style: {args.style}. "
                "Recreate the exact same scene composition, camera movements, and timing "
                "but as animation. Keep the same actions, pacing, and energy. "
                "NO TEXT, NO LABELS, NO WATERMARKS anywhere in the frame. "
                "Clean, vibrant, high quality animation with smooth motion."
            ),
            api_key=settings.gemini_api_key,
            model=settings.trend_analysis_model,
        )

    adapted_shots = adapted.get("shot_breakdown", [])
    print(f"\nAdapted {len(adapted_shots)} shots:")
    for i, s in enumerate(adapted_shots):
        trans = s.get("transition_type", "?")
        desc = str(s.get("description", ""))[:70]
        print(f"  {i + 1}. [{trans}] {s.get('duration_sec', 0)}s - {desc}")

    # --- Step 5: Create project + shots ---
    print("\n=== Step 5: Creating project & shots ===")
    await init_db()

    async with async_session() as session:
        project = Project(
            name=f"TikTok Remix - {args.niche} ({args.style})",
            description=f"Animation remake of viral TikTok: {video_url}",
            target_platform="tiktok",
            style_mood=args.style,
            duration_target=int(analysis.get("pacing", {}).get("total_duration", 30)),
            key_message="",
            tool_preference=args.tool,
        )
        session.add(project)
        await session.flush()

        plans = create_shot_plans_from_analysis(adapted, project)

        for plan in plans:
            tp = generate_tool_prompt(plan, project)
            shot = Shot(
                project_id=project.id,
                order_index=plan.order_index,
                name=plan.name,
                shot_type=plan.shot_type,
                tool=plan.tool,
                prompt=tp.prompt,
                negative_prompt=tp.negative_prompt,
                duration=plan.duration,
                width=plan.width,
                height=plan.height,
                lora_name=tp.lora_name,
                lora_strength=tp.lora_strength,
                transition_type=plan.transition_type,
                status="pending",
            )
            session.add(shot)

        await session.commit()

        # Save original video into project output for comparison
        project_dl = Path("output") / project.id / "source"
        project_dl.mkdir(parents=True, exist_ok=True)
        source_copy = project_dl / f"original{video_path.suffix}"
        shutil.copy2(video_path, source_copy)

        # Save analysis
        analysis_path = project_dl / "analysis.json"
        analysis_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=True))
        adapted_path = project_dl / "adapted.json"
        adapted_path.write_text(json.dumps(adapted, indent=2, ensure_ascii=True))

        print(f"Project ID:  {project.id}")
        print(f"Shots:       {len(plans)}")
        print(f"Original:    {source_copy}")
        print(f"Analysis:    {analysis_path}")

    # --- Step 6: Generate (optional) ---
    if args.generate:
        import httpx

        print("\n=== Step 6: Starting generation ===")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"http://localhost:8000/api/projects/{project.id}/generate"
            )
            job = resp.json()
            job_id = job["id"]
            print(f"Job {job_id} started — {job['total_shots']} shots")

            # Poll until done
            while True:
                await asyncio.sleep(15)
                resp = await client.get(f"http://localhost:8000/api/jobs/{job_id}")
                j = resp.json()
                status = j["status"]
                shot_num = j["current_shot_index"] + 1
                total = j["total_shots"]
                pct = j["progress"]
                print(f"  {status} | shot {shot_num}/{total} | {pct:.0f}% | {j['message']}")

                if status in ("completed", "failed"):
                    if status == "completed":
                        print(f"\nDone! Final video: {j['output_path']}")
                        print(f"Original for comparison: {source_copy}")
                    else:
                        print(f"\nFailed: {j['error']}")
                    break
    else:
        print(f"\nReady! To generate:")
        print(f"  curl -X POST http://localhost:8000/api/projects/{project.id}/generate")
        print(f"\nOr re-run with --generate flag:")
        print(f"  uv run python -m scripts.tiktok_remix --url \"{video_url}\" --generate")


if __name__ == "__main__":
    asyncio.run(main())
