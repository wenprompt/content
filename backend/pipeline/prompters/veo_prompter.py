"""Veo 3.1 prompt pipeline — dialogue, character consistency, cinematic, complex action.

5-element formula: Camera Work -> Subject -> Action -> Setting -> Style & Audio
Target prompt length: 75-125 words. No negative prompts — phrase exclusions positively.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.pipeline.prompt_generator import ToolPrompt

if TYPE_CHECKING:
    from backend.models import Project
    from backend.pipeline.brief_parser import ShotPlan

# ── Veo presets ─────────────────────────────────────────────────────────────

VEO_PRESETS: dict[str, dict[str, object]] = {
    "product": {"duration": 6, "aspect_ratio": "16:9"},
    "dialogue": {"duration": 8, "aspect_ratio": "16:9"},
    "action": {"duration": 6, "aspect_ratio": "16:9"},
    "b_roll": {"duration": 8, "aspect_ratio": "16:9"},
    "tiktok": {"duration": 8, "aspect_ratio": "9:16"},
}


# ── Prompt builder ──────────────────────────────────────────────────────────


def build_veo_prompt(
    shot: ShotPlan,
    project: Project,
    content_type: str = "",
) -> ToolPrompt:
    """Build a Veo 3.1 prompt using the 5-element formula (75-125 words target).

    Elements:
    1. Camera work — shot type + movement + lens feel
    2. Subject — detailed appearance from description
    3. Action — specific verbs in beats
    4. Setting — location, time, atmosphere
    5. Style & Audio — aesthetic + SFX/dialogue/ambient

    No negative prompts — exclusions phrased positively at the end.
    """
    parts: list[str] = []

    # 1. Camera work
    camera = shot.camera_movement.replace("_", " ")
    parts.append(f"A cinematic {camera} shot.")

    # 2-3. Subject and action (from description)
    parts.append(shot.description.rstrip(".") + ".")

    # 4. Setting / atmosphere
    style = project.style_mood or "cinematic"
    parts.append(f"The atmosphere is {style}.")

    # Key message as context
    if project.key_message:
        parts.append(project.key_message.rstrip(".") + ".")

    # Lighting
    if shot.lighting:
        parts.append(shot.lighting.rstrip(".") + ".")

    # 5. Audio — Veo 3.1 supports native audio generation
    if shot.audio:
        audio_text = shot.audio.strip()
        # Preserve structured audio (SFX:, dialogue in quotes)
        # but clean up bare "Audio:" or "Sound:" prefixes
        for prefix in ("Audio:", "Sound:"):
            if audio_text.lower().startswith(prefix.lower()):
                audio_text = audio_text[len(prefix):].strip()
        if audio_text:
            parts.append(f"SFX: {audio_text.rstrip('.')}.")

    # Positive exclusions instead of negative prompts
    parts.append("Sharp focus, no text overlays, no watermarks.")

    prompt = " ".join(parts)

    return ToolPrompt(
        prompt=prompt,
        negative_prompt="",  # Veo does not use negative prompts
        lora_name="",
        lora_strength=0.0,
    )
