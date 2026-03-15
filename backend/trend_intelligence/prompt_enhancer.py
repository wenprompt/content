"""Create shot plans from trend analysis and generate tool-specific prompts."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from google import genai
from google.genai import types

from backend.pipeline.brief_parser import (
    MAX_DURATION_PER_TOOL,
    MIN_DURATION_PER_TOOL,
    PLATFORM_DIMENSIONS,
    ShotPlan,
)
from backend.pipeline.prompt_generator import generate_tool_prompt

if TYPE_CHECKING:
    from backend.models import Project

logger = logging.getLogger(__name__)

# Map common camera movement descriptions to our LoRA names
CAMERA_MOVEMENT_ALIASES: dict[str, str] = {
    "static": "static",
    "still": "static",
    "pan_left": "dolly_left",
    "pan_right": "dolly_right",
    "pan left": "dolly_left",
    "pan right": "dolly_right",
    "zoom_in": "dolly_in",
    "zoom in": "dolly_in",
    "push_in": "dolly_in",
    "push in": "dolly_in",
    "zoom_out": "dolly_out",
    "zoom out": "dolly_out",
    "pull_out": "dolly_out",
    "pull out": "dolly_out",
    "tilt_up": "jib_up",
    "tilt up": "jib_up",
    "crane_up": "jib_up",
    "crane up": "jib_up",
    "tilt_down": "jib_down",
    "tilt down": "jib_down",
    "crane_down": "jib_down",
    "crane down": "jib_down",
    "dolly_in": "dolly_in",
    "dolly_out": "dolly_out",
    "dolly_left": "dolly_left",
    "dolly_right": "dolly_right",
    "jib_up": "jib_up",
    "jib_down": "jib_down",
    "tracking": "dolly_right",
}


def _normalize_camera_movement(raw: str) -> str:
    """Normalize a camera movement description to one of our supported LoRA names."""
    cleaned = raw.strip().lower().replace("-", "_")
    return CAMERA_MOVEMENT_ALIASES.get(cleaned, "static")


ADAPT_PROMPT = """\
You are a video ad creative director. You have an analysis of a viral video ad.
Your job is to adapt the shot breakdown for a NEW product while keeping the same:
- Number of shots
- Camera movements
- Shot durations
- Pacing and energy
- Visual style (lighting, aesthetic)
- Content structure pattern

Original analysis:
{analysis_json}

NEW PRODUCT: {product_name}
PRODUCT DESCRIPTION: {product_description}

Rewrite ONLY the "shot_breakdown" array. Keep the same number of shots, same camera_movement,
and same duration_sec for each shot. Change the "description" to feature the new product
instead of the original. Maintain the same creative concept (e.g., if the original shows
product variety, show variety of the new product).

IMPORTANT RULES FOR DESCRIPTIONS:
- Descriptions should be VISUAL ONLY — describe what is seen, not what is heard.
- NEVER include speech bubbles, word balloons, text overlays, captions, subtitles,
  or any text in the visual description. The AI image/video generator cannot render text.
- If the original has dialogue or text, convert it to visual actions instead
  (e.g., "character speaks excitedly" instead of "character says 'wow!'").

For each shot, decide the "transition_type":
- "hard_cut": completely new scene/subject — a fresh reference image will be generated.
  Use when: different character, different location, different angle/setup, time jump.
- "last_frame": the shot continues from the previous shot's last frame — smooth visual continuity.
  Use when: same scene continues (e.g., camera keeps moving, action progresses, character
  continues moving in the same space). This creates seamless shot chaining.

Think carefully about continuity: if two consecutive shots show the same character doing a
continuous action in the same space, use "last_frame". If the scene/subject changes, use "hard_cut".

For each shot, also provide an "audio" description:
- Describe what should be HEARD during this shot (ambient sounds, music, sound effects, speech).
- For speech, write it naturally: "Character says: Hello everyone!" or "Narrator: Welcome to..."
- For ambient: "birds chirping, gentle wind", "busy city traffic", "upbeat electronic music"
- Audio is generated together with the video by the AI model.

Return ONLY a JSON array of shot objects with these fields:
- timestamp (keep original)
- description (rewritten visual description — NO text/speech bubbles/word balloons)
- camera_movement (keep original)
- duration_sec (keep original)
- transition_type ("hard_cut" or "last_frame")
- audio (what should be heard: music, sound effects, speech, ambient)
"""

STORY_ADAPT_PROMPT = """\
You are a video creative director. You have TWO inputs:
1. A structural analysis of a viral video (camera movements, durations, pacing, shot count)
2. A human-written story description that explains what the video is ACTUALLY about

Your job: rewrite each shot's visual description to match the STORY while keeping Gemini's
structural data (camera movements, durations, shot count, pacing).

The human description is the ground truth for WHAT happens. Gemini's analysis is the ground
truth for HOW it's filmed (camera, timing, cuts).

=== GEMINI ANALYSIS (structure only) ===
{analysis_json}

=== STYLE ===
{style}

=== CHARACTER ===
{character_description}

=== STORY (what actually happens) ===
{story}

RULES:
1. CHARACTER CONSISTENCY: The character description above must appear IDENTICALLY in EVERY shot
   description. Use the exact same appearance details (hair, eyes, clothes, features) so the
   AI generates a visually consistent character across all shots. Copy-paste the character
   description into each shot — do NOT paraphrase or vary it.

2. VISUAL ONLY: Describe what is SEEN, not heard. NO speech bubbles, word balloons, text
   overlays, captions, or any text. Convert dialogue to actions/expressions.

3. TRANSITIONS:
   - "hard_cut": scene/location/angle changes — generates a NEW reference image
   - "last_frame": continuous action in the same space — chains from previous shot's last frame
   Think about what makes visual sense: same character continuing an action = last_frame.
   New scene or dramatic angle change = hard_cut.

4. AUDIO: Describe what should be HEARD (music, sound effects, ambient, speech).
   Audio is generated together with the video.

5. Keep the same number of shots, camera_movement, and duration_sec from the analysis.

Return ONLY a JSON array of shot objects:
- timestamp (from analysis)
- description (visual description with FULL character description included)
- camera_movement (from analysis)
- duration_sec (from analysis)
- transition_type ("hard_cut" or "last_frame")
- audio (what should be heard)
"""


async def adapt_analysis_for_product(
    analysis: dict[str, Any],
    product_name: str,
    product_description: str,
    api_key: str,
    model: str = "gemini-3.1-pro-preview",
) -> dict[str, Any]:
    """Rewrite analysis shot descriptions for a new product using Gemini.

    Keeps the same structure, camera movements, durations, and pacing
    but adapts all descriptions to feature the new product.
    """
    client = genai.Client(api_key=api_key)

    prompt = ADAPT_PROMPT.format(
        analysis_json=json.dumps(analysis, indent=2),
        product_name=product_name,
        product_description=product_description,
    )

    return await _call_adaptation(client, model, prompt, product_name)


async def adapt_analysis_with_story(
    analysis: dict[str, Any],
    story: str,
    style: str,
    character_description: str,
    api_key: str,
    model: str = "gemini-3.1-pro-preview",
) -> dict[str, Any]:
    """Rewrite analysis using a user-provided story as creative direction.

    The story is the ground truth for WHAT happens in each shot.
    Gemini's analysis provides the structure (camera, timing, pacing).
    Character description is repeated identically in every shot for consistency.
    """
    client = genai.Client(api_key=api_key)

    prompt = STORY_ADAPT_PROMPT.format(
        analysis_json=json.dumps(analysis, indent=2),
        style=style,
        character_description=character_description,
        story=story,
    )

    return await _call_adaptation(client, model, prompt, style)


async def _call_adaptation(
    client: genai.Client,
    model: str,
    prompt: str,
    label: str,
) -> dict[str, Any]:
    """Shared adaptation call — sends prompt, parses response."""
    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    if not response.text:
        raise ValueError("Empty response from Gemini adaptation")

    parsed: Any = json.loads(response.text)
    # Gemini may wrap in an array or return the array directly
    if isinstance(parsed, dict) and "shot_breakdown" in parsed:
        new_shots = parsed["shot_breakdown"]
    elif isinstance(parsed, list):
        new_shots = parsed
    else:
        raise ValueError(f"Unexpected response format: {type(parsed)}")

    logger.info("Adapted %d shots for %r", len(new_shots), label)

    # Return as analysis-shaped dict with new shot_breakdown
    return {"shot_breakdown": new_shots}


_SORA_SIGNALS = frozenset({
    "animation", "anime", "cartoon", "3d render", "pixar",
    "stylized", "explosion", "chase", "shatter", "sprint",
})

_CHARACTER_SIGNALS = frozenset({
    "person", "man", "woman", "character", "people",
    "he ", "she ", "they ", "someone",
})

_DIALOGUE_SIGNALS = frozenset({
    "says", "speaks", "talking", "dialogue", "narrator",
    "voice", "conversation",
})


def _select_tool(shot: dict[str, Any], content_type: str, project: Project) -> str:
    """Pick the best generation tool for a shot.

    Default: veo (best multi-shot consistency + native audio).
    Route to sora for stylized animation, complex physics, or pure atmospheric B-roll.
    Route to ltx only when explicitly preferred.
    """
    if project.tool_preference not in ("auto", ""):
        return project.tool_preference

    desc = str(shot.get("description", "")).lower()
    audio = str(shot.get("audio", "")).lower()

    # Sora: stylized animation or complex physics
    if any(s in desc for s in _SORA_SIGNALS):
        return "sora"

    # Sora: pure atmospheric B-roll (no characters / dialogue)
    has_characters = any(s in desc for s in _CHARACTER_SIGNALS)
    has_dialogue = any(s in audio for s in _DIALOGUE_SIGNALS)
    if content_type == "b_roll" and not has_characters and not has_dialogue:
        return "sora"

    # Default: Veo (best for multi-shot consistency + native audio)
    return "veo"


def create_shot_plans_from_analysis(
    analysis: dict[str, Any],
    project: Project,
) -> list[ShotPlan]:
    """Create ShotPlans from a Gemini analysis dict and a project.

    Uses the shot_breakdown from analysis to create matching shots,
    mapping camera movements to LTX camera LoRAs.
    """
    shot_breakdown: list[dict[str, Any]] = analysis.get("shot_breakdown", [])
    if not shot_breakdown:
        # Fallback: create a single shot from the analysis
        shot_breakdown = [{
            "description": analysis.get("content_structure", {}).get("pattern", "dynamic shot"),
            "camera_movement": "static",
            "duration_sec": analysis.get("pacing", {}).get("total_duration", 5.0),
        }]

    width, height = PLATFORM_DIMENSIONS.get(project.target_platform, (1920, 1080))

    # Extract style info from analysis
    visual_style = analysis.get("visual_style", {})
    lighting = visual_style.get("lighting", "")
    aesthetic = visual_style.get("aesthetic", "")

    # Infer content_type from analysis format_type
    content_structure = analysis.get("content_structure", {})
    format_type = str(content_structure.get("format_type", "")).lower()
    # Map common format types to our content presets
    format_to_content: dict[str, str] = {
        "product": "product", "product_ad": "product", "advertisement": "product",
        "b_roll": "b_roll", "b-roll": "b_roll", "atmospheric": "b_roll",
        "food": "food", "cooking": "food", "recipe": "food",
        "fashion": "fashion", "outfit": "fashion", "lookbook": "fashion",
        "talking_head": "talking_head", "interview": "talking_head",
        "architecture": "architecture", "real_estate": "architecture",
        "nature": "nature", "landscape": "nature",
        "slow_motion": "slow_motion", "slowmo": "slow_motion",
    }
    inferred_content_type = format_to_content.get(format_type, "")

    plans: list[ShotPlan] = []
    for i, shot in enumerate(shot_breakdown):
        camera_raw = str(shot.get("camera_movement", "static"))
        camera_movement = _normalize_camera_movement(camera_raw)

        # Select tool per-shot based on content signals
        tool = _select_tool(shot, inferred_content_type, project)

        duration = float(shot.get("duration_sec", 5.0))
        # Clamp to tool-specific duration bounds
        max_dur = MAX_DURATION_PER_TOOL.get(tool, 20.0)
        min_dur = MIN_DURATION_PER_TOOL.get(tool, 2.0)
        duration = max(min(duration, max_dur), min_dur)

        # Sora doesn't support I2V yet; Veo does
        shot_type = "text_to_video" if tool == "sora" else "image_to_video"

        # First shot is always hard_cut; otherwise respect per-shot transition
        transition = "hard_cut" if i == 0 else str(shot.get("transition_type", "hard_cut"))

        # Build description enriched with style
        description = str(shot.get("description", f"Shot {i + 1}"))

        # Build lighting from analysis
        shot_lighting = lighting
        if not shot_lighting and aesthetic:
            shot_lighting = aesthetic

        # Audio: prefer per-shot audio from adaptation, fallback to global
        audio = str(shot.get("audio", ""))
        if not audio:
            audio_info = analysis.get("audio", {})
            if audio_info:
                genre = audio_info.get("music_genre", "")
                bpm = audio_info.get("music_tempo_bpm", 0)
                if genre:
                    audio = f"{genre} music"
                    if bpm:
                        audio += f" at {bpm} BPM"

        plans.append(ShotPlan(
            name=f"Shot {i + 1}",
            order_index=i,
            shot_type=shot_type,
            tool=tool,
            description=description,
            camera_movement=camera_movement,
            camera_strength=0.85,
            duration=duration,
            width=width,
            height=height,
            transition_type=transition,
            lighting=shot_lighting,
            audio=audio,
            content_type=inferred_content_type,
        ))

    return plans


def generate_prompts(
    shot_plans: list[ShotPlan],
    project: Project,
) -> list[ShotPlan]:
    """Generate tool-specific prompts for each shot plan.

    Enriches prompts with analysis-derived style/mood/lighting.
    Returns the same ShotPlan list with prompt data attached via ToolPrompt.
    """
    # Validate that prompts can be generated for each plan
    for plan in shot_plans:
        generate_tool_prompt(plan, project)

    return shot_plans
