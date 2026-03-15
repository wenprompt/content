"""LTX 2.3 food content — 4-shot demo with cooking sounds woven naturally.

Demonstrates LTX sweet spot: food photography/videography with static and
dolly_in cameras, naturally woven audio (sizzling, chopping, plating sounds).

Usage:
    uv run python -m scripts.ltx_food_demo
    uv run python -m scripts.ltx_food_demo --generate
"""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# ── Creative brief ──────────────────────────────────────────────────────────

STYLE = "warm editorial food photography, shallow depth of field, natural daylight kitchen"

SHOTS = [
    {
        "name": "Overhead Ingredients",
        "description": (
            "A beautifully arranged spread of fresh ingredients on a marble "
            "countertop seen from directly above. Ripe tomatoes, fresh basil, "
            "olive oil in a glass bottle, garlic cloves, and hand-made pasta "
            "sheets arranged in a pleasing composition."
        ),
        "camera_movement": "jib_down",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Soft natural daylight from a kitchen window, warm and inviting",
        "audio": (
            "gentle kitchen ambiance, a wooden cutting board being set down, "
            "olive oil glugging softly from the bottle"
        ),
    },
    {
        "name": "Cooking Action",
        "description": (
            "Fresh pasta hits a hot cast-iron pan with olive oil. Steam rises "
            "immediately as garlic sizzles alongside. A hand tosses the pasta "
            "with a gentle flick of the wrist, sending small oil droplets "
            "into the warm light."
        ),
        "camera_movement": "static",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Warm side light catching steam and oil droplets, dramatic kitchen glow",
        "audio": (
            "pasta hitting hot oil with a satisfying sizzle, garlic crackling, "
            "pan scraping softly against the burner grate"
        ),
    },
    {
        "name": "Plating Detail",
        "description": (
            "Hands carefully twirl pasta onto a warm ceramic plate using tongs "
            "and a fork, creating a neat nest. Sauce is spooned over in a "
            "circular motion. Fresh basil leaves are placed on top one by one."
        ),
        "camera_movement": "dolly_in",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Focused overhead light on the plate, soft bokeh background",
        "audio": (
            "tongs clicking against the plate rim, sauce drizzling smoothly, "
            "a final basil leaf placed with a soft pat"
        ),
    },
    {
        "name": "Final Dish Hero",
        "description": (
            "The finished pasta dish on a rustic wooden table, steam rising "
            "gently from the sauce. A fork lifts a perfect twirl of pasta, "
            "stretching golden strands. The background is a blurred warm "
            "kitchen scene."
        ),
        "camera_movement": "static",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Golden warm light from behind, rim-lighting the rising steam",
        "audio": (
            "steam hissing softly from the hot dish, fork clinking against "
            "ceramic, a contented exhale"
        ),
    },
]


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LTX Food Demo — 4-shot cooking content")
    parser.add_argument("--generate", action="store_true", help="Auto-start generation")
    parser.add_argument("--t2v", action="store_true", help="Use text-to-video (skip reference images)")
    args = parser.parse_args()

    from backend.database import async_session, init_db
    from backend.models import Project, Shot
    from backend.pipeline.brief_parser import ShotPlan
    from backend.pipeline.prompt_generator import generate_tool_prompt

    await init_db()

    async with async_session() as session:
        project = Project(
            name="LTX Food Demo — Fresh Pasta",
            description="4-shot food content showcasing LTX with woven cooking audio",
            target_platform="instagram",
            style_mood=STYLE,
            duration_target=20,
            key_message="",
            tool_preference="ltx",
        )
        session.add(project)
        await session.flush()

        print(f"\n=== LTX Food Demo — {len(SHOTS)} shots ===\n")
        print(f"Project ID: {project.id}")
        print(f"Content type: food (I2V strength 0.6)\n")

        shot_type = "text_to_video" if args.t2v else "image_to_video"

        for i, s in enumerate(SHOTS):
            plan = ShotPlan(
                name=s["name"],
                order_index=i,
                shot_type=shot_type,
                tool="ltx",
                description=s["description"],
                camera_movement=s["camera_movement"],
                camera_strength=0.85,
                duration=s["duration"],
                width=1280,
                height=720,
                transition_type=s["transition_type"],
                lighting=s["lighting"],
                audio=s["audio"],
                content_type="food",
            )

            tp = generate_tool_prompt(plan, project, content_type="food")

            shot = Shot(
                project_id=project.id,
                order_index=i,
                name=s["name"],
                shot_type=shot_type,
                tool="ltx",
                prompt=tp.prompt,
                negative_prompt=tp.negative_prompt,
                duration=s["duration"],
                width=1280,
                height=720,
                lora_name=tp.lora_name,
                lora_strength=tp.lora_strength,
                transition_type=s["transition_type"],
                status="pending",
            )
            session.add(shot)

            lora = tp.lora_name.split("-")[-1].replace(".safetensors", "") if tp.lora_name else "none"
            print(f"  Shot {i + 1}: {s['name']}")
            print(f"    [{s['transition_type']}] {s['duration']}s | cam: {s['camera_movement']} | lora: {lora}")
            print(f"    Prompt: {tp.prompt[:120]}...")
            print()

        await session.commit()
        print(f"Saved {len(SHOTS)} shots to project {project.id}")

    if args.generate:
        import httpx

        print("\n=== Starting generation ===")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"http://localhost:8000/api/projects/{project.id}/generate"
            )
            job = resp.json()
            job_id = job["id"]
            print(f"Job {job_id} started — {job['total_shots']} shots\n")

            while True:
                await asyncio.sleep(15)
                resp = await client.get(f"http://localhost:8000/api/jobs/{job_id}")
                j = resp.json()
                status = j["status"]
                print(f"  {status} | shot {j['current_shot_index'] + 1}/{j['total_shots']} | {j['progress']:.0f}% | {j['message']}")
                if status in ("completed", "failed"):
                    if status == "completed":
                        print(f"\nDone! Final video: {j['output_path']}")
                    else:
                        print(f"\nFailed: {j['error']}")
                    break
    else:
        print(f"\nTo generate:")
        print(f"  curl -X POST http://localhost:8000/api/projects/{project.id}/generate")


if __name__ == "__main__":
    asyncio.run(main())
