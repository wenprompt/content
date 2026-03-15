"""Sora 2 prompt pipeline — photorealism, physics, cinematic lighting, stylized animation.

Structure: [VISUAL DESCRIPTION] + [AUDIO] sections.
Core Four: Style -> Subject -> Action -> Environment, plus [AUDIO] section.
Keep under 200 words total, one dominant action per clip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.pipeline.prompt_generator import ToolPrompt

if TYPE_CHECKING:
    from backend.models import Project
    from backend.pipeline.brief_parser import ShotPlan

# ── Sora presets ────────────────────────────────────────────────────────────

SORA_PRESETS: dict[str, dict[str, object]] = {
    "product": {"duration": 8, "resolution": "1080p", "model": "sora-2-pro"},
    "b_roll": {"duration": 8, "resolution": "720p", "model": "sora-2"},
    "cinematic": {"duration": 12, "resolution": "1080p", "model": "sora-2-pro"},
    "tiktok": {"duration": 8, "resolution": "720p", "model": "sora-2"},
}


# ── Prompt builder ──────────────────────────────────────────────────────────


def build_sora_prompt(
    shot: ShotPlan,
    project: Project,
    content_type: str = "",
) -> ToolPrompt:
    """Build a Sora 2 prompt with [VISUAL DESCRIPTION] and [AUDIO] sections.

    Visual section follows Core Four:
    1. Style — aesthetic/mood
    2. Subject + Action — in beats, one dominant action
    3. Camera + Lens
    4. Environment + Lighting

    Audio section:
    - Dialogue in quotes, SFX descriptions, ambient, music

    Keep under 200 words total.
    """
    visual_parts: list[str] = []
    audio_parts: list[str] = []

    # ── VISUAL DESCRIPTION ──────────────────────────────────────────────
    visual_parts.append("[VISUAL DESCRIPTION]")

    # 1. Style
    style = project.style_mood or "cinematic"
    visual_parts.append(f"Style: {style}.")

    # 2. Subject + Action
    visual_parts.append(shot.description.rstrip(".") + ".")

    # Key message
    if project.key_message:
        visual_parts.append(project.key_message.rstrip(".") + ".")

    # 3. Camera + Lens
    camera = shot.camera_movement.replace("_", " ")
    visual_parts.append(f"Camera: {camera}.")

    # 4. Environment + Lighting
    if shot.lighting:
        visual_parts.append(f"Lighting: {shot.lighting.rstrip('.')}.")

    # ── AUDIO ───────────────────────────────────────────────────────────
    audio_parts.append("[AUDIO]")

    if shot.audio:
        audio_text = shot.audio.strip()
        # Clean up any existing section prefix
        for prefix in ("Audio:", "Sound:", "SFX:"):
            if audio_text.lower().startswith(prefix.lower()):
                audio_text = audio_text[len(prefix):].strip()
        audio_parts.append(audio_text.rstrip(".") + ".")
    else:
        audio_parts.append("Ambient sound.")

    prompt = " ".join(visual_parts) + " " + " ".join(audio_parts)

    return ToolPrompt(
        prompt=prompt,
        negative_prompt="",  # Sora does not use negative prompts
        lora_name="",
        lora_strength=0.0,
    )
