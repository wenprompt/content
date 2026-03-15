"""Parse a project brief into a structured shot plan using Gemini or OpenAI."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.models import Project

PLATFORM_DIMENSIONS: dict[str, tuple[int, int]] = {
    "tiktok": (768, 1344),
    "instagram": (768, 1344),
    "facebook": (1280, 720),
    "youtube": (1280, 720),
}

MAX_DURATION_PER_TOOL: dict[str, float] = {"ltx": 20.0, "veo": 8.0, "sora": 12.0}
MIN_DURATION_PER_TOOL: dict[str, float] = {"ltx": 2.0, "veo": 4.0, "sora": 4.0}

SYSTEM_PROMPT = """\
You are a video production planner. Given a creative brief, output a JSON array of shot objects.

Each shot object MUST have exactly these fields:
- "name": short descriptive name (e.g. "Hero Product Reveal")
- "order_index": integer starting at 0
- "shot_type": always "image_to_video"
- "tool": one of "ltx", "veo", "sora"
- "description": creative description of what happens in the shot (2-3 sentences)
- "camera_movement": one of "dolly_in", "dolly_out", "dolly_left", "dolly_right", \
"jib_up", "jib_down", "static"
- "camera_strength": float between 0.7 and 1.0 (LoRA strength, only used by LTX)
- "duration": float in seconds
- "transition_type": "hard_cut" for first shot, then "last_frame" or "extend" for subsequent shots
- "lighting": lighting description (e.g. "warm golden hour backlight")
- "audio": audio/sound description (e.g. "upbeat electronic music with bass drop")

Shot count guidelines by content type:
- product_ad: 6 shots (hook, product reveal, features, lifestyle, social proof, CTA)
- short_clip: 5 shots (hook, build, climax, resolve, CTA)
- b_roll: 8-12 shots (varied atmospheric and detail shots)
- animation: 5 shots (intro, build, transform, showcase, outro)

Tool selection rules (when tool_preference is "auto"):
- Default to "veo" (best multi-shot quality, native audio with lip-sync, 4K)
- Use "sora" for stylized animation (anime, cartoon, 3D, pixar), complex physics \
(explosions, chase, shatter), or atmospheric B-roll without characters
- Use "ltx" only when explicitly preferred (free, local, camera LoRAs)

Camera movement guidelines:
- static: talking heads, text overlays, product displays
- dolly_in: reveals, dramatic emphasis, product focus
- dolly_out: establishing shots, context reveals
- dolly_left/dolly_right: tracking, panning across scenes
- jib_up: epic reveals, ascending energy
- jib_down: intimate, descending to detail

Output ONLY a JSON array. No markdown, no explanation."""


@dataclass
class ShotPlan:
    name: str
    order_index: int
    shot_type: str
    tool: str
    description: str
    camera_movement: str
    camera_strength: float
    duration: float
    width: int
    height: int
    transition_type: str
    lighting: str
    audio: str
    content_type: str = ""


def _build_user_prompt(project: Project) -> str:
    return (
        f"Project: {project.name}\n"
        f"Description: {project.description}\n"
        f"Content type: {project.content_type}\n"
        f"Target platform: {project.target_platform}\n"
        f"Style/mood: {project.style_mood or 'not specified'}\n"
        f"Duration target: {project.duration_target} seconds total\n"
        f"Audio needs: {project.audio_needs or 'not specified'}\n"
        f"Key message: {project.key_message or 'not specified'}\n"
        f"Tool preference: {project.tool_preference}"
    )


async def _call_gemini(
    api_key: str, model: str, system_prompt: str, user_prompt: str
) -> list[dict[str, Any]]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = await client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )
    if not response.text:
        raise ValueError("Empty response from Gemini")
    data: list[dict[str, Any]] = json.loads(response.text)
    return data


async def _call_openai(
    api_key: str, model: str, system_prompt: str, user_prompt: str
) -> list[dict[str, Any]]:
    import openai

    client = openai.AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    text = response.choices[0].message.content or ""
    if not text:
        raise ValueError("Empty response from OpenAI")
    parsed = json.loads(text)
    # OpenAI json_object mode may wrap in {"shots": [...]}
    if isinstance(parsed, dict):
        for v in parsed.values():
            if isinstance(v, list):
                return v
        raise ValueError("Could not find shot array in OpenAI response")
    result: list[dict[str, Any]] = parsed
    return result


def _postprocess(
    raw_shots: list[dict[str, Any]], project: Project
) -> list[ShotPlan]:
    width, height = PLATFORM_DIMENSIONS.get(
        project.target_platform, (1920, 1080)
    )

    plans: list[ShotPlan] = []
    for i, raw in enumerate(raw_shots):
        tool = str(raw.get("tool", "ltx"))
        if project.tool_preference != "auto":
            tool = project.tool_preference

        max_dur = MAX_DURATION_PER_TOOL.get(tool, 20.0)
        min_dur = MIN_DURATION_PER_TOOL.get(tool, 2.0)
        duration = max(min(float(raw.get("duration", 5.0)), max_dur), min_dur)

        transition = str(raw.get("transition_type", "last_frame"))
        if i == 0:
            transition = "hard_cut"

        plans.append(
            ShotPlan(
                name=str(raw.get("name", f"Shot {i + 1}")),
                order_index=i,
                shot_type="image_to_video",
                tool=tool,
                description=str(raw.get("description", "")),
                camera_movement=str(raw.get("camera_movement", "static")),
                camera_strength=float(raw.get("camera_strength", 0.85)),
                duration=duration,
                width=width,
                height=height,
                transition_type=transition,
                lighting=str(raw.get("lighting", "")),
                audio=str(raw.get("audio", "")),
            )
        )
    return plans


async def parse_brief(
    project: Project,
    provider: str = "gemini",
    api_key: str = "",
    model: str = "gemini-2.5-flash",
) -> list[ShotPlan]:
    """Parse a project brief into a list of ShotPlans using an LLM."""
    if not api_key:
        raise ValueError("API key is required for brief parsing")

    user_prompt = _build_user_prompt(project)

    if provider == "openai":
        raw_shots = await _call_openai(api_key, model, SYSTEM_PROMPT, user_prompt)
    else:
        raw_shots = await _call_gemini(api_key, model, SYSTEM_PROMPT, user_prompt)

    return _postprocess(raw_shots, project)
