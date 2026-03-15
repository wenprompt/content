"""Luxury Watch Showcase — 6-shot product + B-roll hybrid.

Combines product hero shots (I2V with reference image for identity lock)
and atmospheric B-roll for lifestyle context.

Usage:
    uv run python -m scripts.watch_showcase
    uv run python -m scripts.watch_showcase --generate
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# ── Creative brief ──────────────────────────────────────────────────────────

REFERENCE_IMAGE = str(Path(__file__).resolve().parent.parent / "docs" / "watch.png")

STYLE = (
    "luxury product cinematography, dramatic chiaroscuro lighting, "
    "rich deep blacks, metallic reflections, shallow depth of field, "
    "editorial watch photography"
)

WATCH = (
    "A Rolex Submariner dive watch with a green ceramic bezel, black dial, "
    "luminous hour markers, date window at 3 o'clock, and polished stainless "
    "steel Oyster bracelet"
)

SHOTS = [
    # ── Product shots (I2V with reference image) ────────────────────────
    {
        "name": "Dark Reveal",
        "description": (
            f"{WATCH} emerges from deep shadow. A single beam of warm light "
            "sweeps slowly across the dial, catching the polished steel case "
            "and igniting the green bezel with a rich emerald glow. The watch "
            "rests on black velvet."
        ),
        "camera_movement": "dolly_in",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Single warm spotlight sweeping across from left, deep black background",
        "audio": (
            "a resonant mechanical tick echoing in silence, "
            "soft velvet texture as light reveals the watch"
        ),
        "content_type": "product",
        "reference_image": REFERENCE_IMAGE,
    },
    {
        "name": "Bezel Macro",
        "description": (
            "Extreme close-up of the green ceramic bezel rotating slowly. "
            "Each engraved minute marker catches light individually. The "
            "polished bevel between bezel and case gleams with razor-sharp "
            "reflections. Microscopic texture of the ceramic surface visible."
        ),
        "camera_movement": "static",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Focused spotlight on bezel edge, deep bokeh on dial behind",
        "audio": (
            "satisfying mechanical click of the bezel rotating, "
            "precise and tactile, quiet room tone"
        ),
        "content_type": "product",
        "reference_image": REFERENCE_IMAGE,
    },
    {
        "name": "Dial Detail",
        "description": (
            "The camera glides across the black dial surface. Luminous hour "
            "markers glow softly green. The sweeping seconds hand moves with "
            "smooth precision. Light plays across the Cyclops lens magnifying "
            "the date window. Steel hands cast tiny shadows on the matte dial."
        ),
        "camera_movement": "dolly_right",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Soft diffused top light with subtle warm fill, dial surface reflections",
        "audio": (
            "the precise sweep of the seconds hand, "
            "a faint mechanical heartbeat of the movement inside"
        ),
        "content_type": "product",
        "reference_image": REFERENCE_IMAGE,
    },
    # ── B-roll atmospheric context ──────────────────────────────────────
    {
        "name": "Ocean Surface",
        "description": (
            "Deep blue ocean water seen from just below the surface. Sunlight "
            "filters through in dancing caustic patterns. Tiny air bubbles "
            "drift upward through shafts of aquamarine light. The surface "
            "ripples gently above."
        ),
        "camera_movement": "jib_up",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Underwater sunlight caustics, deep blue gradient to surface brightness",
        "audio": (
            "muffled underwater ambiance, gentle water movement, "
            "distant bubbles rising to the surface"
        ),
        "content_type": "b_roll",
        "reference_image": "",
    },
    {
        "name": "Wrist Lifestyle",
        "description": (
            f"{WATCH} on a man's wrist resting on the polished mahogany rail "
            "of a yacht. Deep blue sea stretches to the horizon behind. "
            "Golden late-afternoon sun warms the steel bracelet. A gentle "
            "breeze catches the sleeve of a navy linen shirt."
        ),
        "camera_movement": "dolly_in",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Golden hour sun from behind, warm rim light on bracelet and wrist",
        "audio": (
            "gentle waves against the yacht hull, warm breeze, "
            "distant seagull, fabric rustling softly"
        ),
        "content_type": "product",
        "reference_image": REFERENCE_IMAGE,
    },
    # ── Final hero ──────────────────────────────────────────────────────
    {
        "name": "Crown Jewel",
        "description": (
            f"{WATCH} standing upright on a reflective black surface. The "
            "camera slowly pulls back to reveal the full watch reflected "
            "perfectly below. Green bezel and luminous markers glow against "
            "the darkness. A subtle light pulse travels across the bracelet "
            "links one by one."
        ),
        "camera_movement": "dolly_out",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Dramatic rim lighting from both sides, reflective black surface, deep shadows",
        "audio": (
            "a deep resonant tone building slowly, "
            "the mechanical heartbeat of the watch filling the silence"
        ),
        "content_type": "product",
        "reference_image": REFERENCE_IMAGE,
    },
]


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Luxury Watch Showcase — product + B-roll")
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
            name="Rolex Submariner — Luxury Watch Showcase",
            description="6-shot product + B-roll showcase for a luxury dive watch",
            target_platform="youtube",
            style_mood=STYLE,
            duration_target=30,
            key_message=WATCH,
            tool_preference="ltx",
        )
        session.add(project)
        await session.flush()

        print(f"\n=== Luxury Watch Showcase — {len(SHOTS)} shots ===\n")
        print(f"Project ID: {project.id}")
        print(f"Reference image: {REFERENCE_IMAGE}\n")

        for i, s in enumerate(SHOTS):
            ct = s["content_type"]
            ref = s["reference_image"]
            shot_type = "text_to_video" if (args.t2v or not ref) else "image_to_video"

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
                content_type=ct,
            )

            tp = generate_tool_prompt(plan, project, content_type=ct)

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
                reference_image=ref,
                status="pending",
            )
            session.add(shot)

            lora = tp.lora_name.split("-")[-1].replace(".safetensors", "") if tp.lora_name else "none"
            ref_label = "YOUR IMAGE" if ref else "AI-generated"
            print(f"  Shot {i + 1}: {s['name']} [{ct}]")
            print(f"    [{s['transition_type']}] {s['duration']}s | cam: {s['camera_movement']} | lora: {lora}")
            print(f"    Ref: {ref_label} | Type: {shot_type}")
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
        print(f"  # or: uv run python -m scripts.watch_showcase --generate")


if __name__ == "__main__":
    asyncio.run(main())
