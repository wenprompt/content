"""LTX 2.3 product showcase — 4-shot demo with I2V identity lock.

Demonstrates LTX sweet spot: product shots with low I2V strength (0.3),
camera LoRA control, and woven audio descriptions.

Usage:
    uv run python -m scripts.ltx_product_demo
    uv run python -m scripts.ltx_product_demo --generate
"""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# ── Creative brief ──────────────────────────────────────────────────────────

STYLE = "clean minimal product photography, soft diffused lighting, neutral studio backdrop"

PRODUCT = "A matte black wireless speaker with brushed aluminum accents and a subtle LED ring"

SHOTS = [
    {
        "name": "Wide Establishing",
        "description": (
            f"{PRODUCT} sits on a pale oak surface against a soft gradient "
            "backdrop. Morning light streams in from the left, casting a long "
            "gentle shadow. The scene is calm and minimal."
        ),
        "camera_movement": "dolly_out",
        "duration": 4.0,
        "transition_type": "hard_cut",
        "lighting": "Soft diffused morning light from the left with gentle shadow fall-off",
        "audio": (
            "a quiet room tone with the faintest hum of bass resonance "
            "as if the speaker is about to play"
        ),
    },
    {
        "name": "Hero Reveal",
        "description": (
            f"The camera approaches {PRODUCT}, revealing the brushed aluminum "
            "texture and the subtle blue LED ring glowing to life. Light plays "
            "across the matte surface."
        ),
        "camera_movement": "dolly_in",
        "duration": 5.0,
        "transition_type": "last_frame",
        "lighting": "Rim light catching the aluminum edge, soft fill from front",
        "audio": (
            "a soft electronic chime as the LED ring activates, "
            "smooth low-frequency hum building gently"
        ),
    },
    {
        "name": "Detail Macro",
        "description": (
            "Extreme close-up of the speaker's brushed aluminum grille pattern. "
            "Each perforation catches light differently, creating a subtle "
            "shimmer across the surface. Dust particles float in the light beam."
        ),
        "camera_movement": "static",
        "duration": 4.0,
        "transition_type": "hard_cut",
        "lighting": "Focused spotlight on grille texture with bokeh background",
        "audio": (
            "crisp high-frequency detail emerging from the grille, "
            "delicate metallic resonance"
        ),
    },
    {
        "name": "Brand Moment",
        "description": (
            f"{PRODUCT} in full view on the oak surface with the LED ring "
            "pulsing softly. The camera pulls back to reveal the full product "
            "in its lifestyle context — a curated desk setup with a plant "
            "and notebook."
        ),
        "camera_movement": "dolly_out",
        "duration": 5.0,
        "transition_type": "hard_cut",
        "lighting": "Warm ambient room light with cool LED accent glow",
        "audio": (
            "warm ambient music fading in, the LED ring pulse synced "
            "with a gentle bass beat"
        ),
    },
]


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LTX Product Demo — 4-shot showcase")
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
            name="LTX Product Demo — Wireless Speaker",
            description="4-shot product showcase demonstrating LTX I2V identity lock",
            target_platform="youtube",
            style_mood=STYLE,
            duration_target=18,
            key_message=PRODUCT,
            tool_preference="ltx",
        )
        session.add(project)
        await session.flush()

        print(f"\n=== LTX Product Demo — {len(SHOTS)} shots ===\n")
        print(f"Project ID: {project.id}")
        print(f"Content type: product (I2V strength 0.3)\n")

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
                content_type="product",
            )

            tp = generate_tool_prompt(plan, project, content_type="product")

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
