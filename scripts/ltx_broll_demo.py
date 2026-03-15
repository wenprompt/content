"""LTX 2.3 atmospheric B-roll — 5-shot demo with scene evolution.

Demonstrates LTX sweet spot: atmospheric B-roll with camera LoRAs,
"Over time, ..." suffixes for gradual scene changes, and woven audio.

Usage:
    uv run python -m scripts.ltx_broll_demo
    uv run python -m scripts.ltx_broll_demo --generate
"""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# ── Creative brief ──────────────────────────────────────────────────────────

STYLE = "cinematic, golden hour warmth, atmospheric depth, natural textures"

SHOTS = [
    {
        "name": "Golden Hour Cityscape",
        "description": (
            "A sprawling cityscape at golden hour, warm sunlight painting "
            "building facades in amber and copper. Long shadows stretch across "
            "empty streets below. Heat haze shimmers above rooftops."
        ),
        "camera_movement": "dolly_right",
        "duration": 6.0,
        "transition_type": "hard_cut",
        "lighting": "Golden hour side light with warm amber tones and deep shadows",
        "audio": (
            "distant traffic hum, a church bell ringing in the distance, "
            "warm breeze rustling through leaves"
        ),
    },
    {
        "name": "Foggy Forest Path",
        "description": (
            "A narrow dirt path winding through a dense forest, morning fog "
            "hanging low between moss-covered tree trunks. Shafts of light "
            "pierce through the canopy, illuminating floating dust particles."
        ),
        "camera_movement": "dolly_in",
        "duration": 7.0,
        "transition_type": "hard_cut",
        "lighting": "Diffused morning light filtering through fog and canopy",
        "audio": (
            "birdsong echoing through the trees, soft footsteps on damp earth, "
            "leaves rustling overhead"
        ),
    },
    {
        "name": "Rain on Cobblestones",
        "description": (
            "Close-up of rain falling on old cobblestones in a European alley. "
            "Each droplet creates concentric ripples in shallow puddles. "
            "Warm light from a café window reflects in the wet stone surface."
        ),
        "camera_movement": "static",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Warm café glow reflecting in wet surfaces, cool ambient rain light",
        "audio": (
            "steady rain pattering on stone, distant café music muffled through glass, "
            "occasional splash of a deeper puddle"
        ),
    },
    {
        "name": "Pre-Dawn Desert Highway",
        "description": (
            "An empty two-lane highway stretching into a vast desert landscape. "
            "The sky shifts from deep indigo to pale orange at the horizon. "
            "A single set of headlights approaches far in the distance."
        ),
        "camera_movement": "jib_up",
        "duration": 7.0,
        "transition_type": "hard_cut",
        "lighting": "Pre-dawn gradient sky casting cool blue on sand, warm orange at horizon",
        "audio": (
            "wind sweeping across open desert, distant engine approaching, "
            "gravel crunching softly"
        ),
    },
    {
        "name": "Lake at Sunrise",
        "description": (
            "A perfectly still mountain lake at sunrise, the water surface "
            "mirroring snow-capped peaks and pink-tinged clouds. A single "
            "rowing boat drifts slowly near the shore."
        ),
        "camera_movement": "dolly_left",
        "duration": 7.0,
        "transition_type": "hard_cut",
        "lighting": "Soft pink sunrise glow reflecting off mirror-still water",
        "audio": (
            "gentle water lapping against the boat hull, a loon calling "
            "across the lake, morning silence"
        ),
    },
]


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LTX B-Roll Demo — 5-shot atmospheric")
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
            name="LTX B-Roll Demo — Atmospheric Landscapes",
            description="5-shot atmospheric B-roll showcasing LTX scene evolution",
            target_platform="youtube",
            style_mood=STYLE,
            duration_target=32,
            key_message="",
            tool_preference="ltx",
        )
        session.add(project)
        await session.flush()

        print(f"\n=== LTX B-Roll Demo — {len(SHOTS)} shots ===\n")
        print(f"Project ID: {project.id}")
        print(f"Content type: b_roll (T2V for creative freedom)\n")

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
                width=1920,
                height=1080,
                transition_type=s["transition_type"],
                lighting=s["lighting"],
                audio=s["audio"],
                content_type="b_roll",
            )

            tp = generate_tool_prompt(plan, project, content_type="b_roll")

            shot = Shot(
                project_id=project.id,
                order_index=i,
                name=s["name"],
                shot_type=shot_type,
                tool="ltx",
                prompt=tp.prompt,
                negative_prompt=tp.negative_prompt,
                duration=s["duration"],
                width=1920,
                height=1080,
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
