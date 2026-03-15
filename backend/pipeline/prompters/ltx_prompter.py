"""LTX 2.3 prompt pipeline — optimized for product shots, B-roll, slow-mo, single-subject.

6-element formula: Scene Anchor -> Subject -> Action -> Camera -> Lighting -> Audio
Audio is woven into the narrative paragraph, NOT prefixed with "Audio:".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.pipeline.prompt_generator import CAMERA_LORA_MAP, ToolPrompt

if TYPE_CHECKING:
    from backend.models import Project
    from backend.pipeline.brief_parser import ShotPlan

# ── Negative prompt sets ────────────────────────────────────────────────────

_STANDARD_NEG = (
    "worst quality, low quality, blurry, pixelated, grainy, distorted, "
    "watermark, text, logo, shaky, glitchy, deformed, morphing, warping, "
    "flicker, temporal artifacts"
)

NEGATIVE_PROMPTS: dict[str, str] = {
    "standard": _STANDARD_NEG,
    "hands_faces": (
        f"{_STANDARD_NEG}, fused fingers, bad anatomy, extra hands, "
        "deformed hands, malformed face"
    ),
    "motion": (
        f"{_STANDARD_NEG}, static, still image, frozen, motion smear, "
        "jitter, stutter"
    ),
}

# ── Content-type presets ────────────────────────────────────────────────────

LTX_PRESETS: dict[str, dict[str, object]] = {
    "product": {
        "width": 1920, "height": 1080, "fps": 24,
        "i2v_strength": 0.3, "neg": "standard",
    },
    "b_roll": {
        "width": 1920, "height": 1080, "fps": 24,
        "i2v_strength": 0.65, "neg": "standard",
    },
    "food": {
        "width": 1920, "height": 1080, "fps": 24,
        "i2v_strength": 0.6, "neg": "standard",
    },
    "slow_motion": {
        "width": 1280, "height": 720, "fps": 48,
        "i2v_strength": 0.6, "neg": "motion",
    },
    "talking_head": {
        "width": 1920, "height": 1080, "fps": 24,
        "i2v_strength": 0.7, "neg": "hands_faces",
    },
    "fashion": {
        "width": 1920, "height": 1080, "fps": 24,
        "i2v_strength": 0.65, "neg": "hands_faces",
    },
    "architecture": {
        "width": 1920, "height": 1080, "fps": 24,
        "i2v_strength": 0.65, "neg": "standard",
    },
    "nature": {
        "width": 1920, "height": 1080, "fps": 24,
        "i2v_strength": 0.65, "neg": "standard",
    },
    "tiktok": {
        "width": 768, "height": 1344, "fps": 24,
        "i2v_strength": 0.65, "neg": "standard",
    },
}

# ── Camera LoRA recommendations per content type ────────────────────────────

CONTENT_CAMERAS: dict[str, list[str]] = {
    "product": ["dolly_in", "static", "dolly_out"],
    "b_roll": ["dolly_left", "dolly_right", "jib_up"],
    "food": ["static", "dolly_in", "jib_down"],
    "fashion": ["dolly_in", "static", "dolly_left"],
    "architecture": ["dolly_left", "dolly_right", "jib_up"],
}

# ── I2V vs T2V routing ─────────────────────────────────────────────────────

# Content types that benefit from I2V (identity lock, composition control)
_I2V_TYPES = {"product", "food", "fashion", "talking_head"}
# Content types that benefit from T2V (creative freedom, more dynamic)
_T2V_TYPES = {"b_roll", "slow_motion", "nature"}


def should_use_i2v(content_type: str) -> bool:
    """Decide whether I2V is preferred for the given content type.

    I2V: product (identity lock), food (composition), fashion (outfit consistency).
    T2V: b_roll (creative freedom), slow_motion (more dynamic range).
    """
    if content_type in _I2V_TYPES:
        return True
    # T2V types get creative freedom; default to I2V for consistency
    return content_type not in _T2V_TYPES


# ── Guardrails ──────────────────────────────────────────────────────────────

_MULTI_CHARACTER_WORDS = {"people", "crowd", "group", "characters", "actors", "dancers"}
_FAST_ACTION_WORDS = {"explosion", "crash", "fight", "chase", "battle", "sprint"}
_TEXT_WORDS = {"text", "logo", "subtitle", "caption", "title card", "word"}
_COMPLEX_PHYSICS = {"water splash", "shatter", "crumble", "collapse", "pour liquid"}
_ANIME_WORDS = {"anime", "manga", "cel-shaded", "chibi"}


def validate_ltx_prompt(description: str) -> list[str]:
    """Return warnings for prompt elements that LTX struggles with.

    Checks for: multiple characters, fast action, text/logos,
    complex physics, anime style (suggest Veo/Sora instead).
    """
    warnings: list[str] = []
    lower = description.lower()

    if any(w in lower for w in _MULTI_CHARACTER_WORDS):
        warnings.append(
            "LTX works best with single subjects. Multiple characters may "
            "cause inconsistency — consider Veo for multi-character scenes."
        )
    if any(w in lower for w in _FAST_ACTION_WORDS):
        warnings.append(
            "Fast action can cause motion artifacts in LTX. Consider "
            "slow_motion preset (48fps) or Sora for complex action."
        )
    if any(w in lower for w in _TEXT_WORDS):
        warnings.append(
            "LTX cannot reliably render text or logos. Remove text "
            "references from the prompt."
        )
    if any(w in lower for w in _COMPLEX_PHYSICS):
        warnings.append(
            "Complex physics (liquid, shattering) may look unnatural in LTX. "
            "Consider Sora for realistic physics."
        )
    if any(w in lower for w in _ANIME_WORDS):
        warnings.append(
            "LTX excels at photorealistic/cinematic content. For anime "
            "styles, consider Sora or Veo."
        )
    return warnings


# ── Prompt builder ──────────────────────────────────────────────────────────


def build_ltx_prompt(
    shot: ShotPlan,
    project: Project,
    content_type: str = "",
) -> ToolPrompt:
    """Build an LTX-optimized prompt using the 6-element formula.

    Elements flow as a natural paragraph:
    1. Scene anchor — "{description} in a {style} style."
    2. Subject — project.key_message with physical cues
    3. Action — embedded in description
    4. Lighting — "{lighting}."
    5. Audio — woven naturally, NOT "Audio: ..." prefix
    6. Camera — SKIP if LoRA active
    + "Over time, ..." suffix for gradual changes (duration > 5s)
    """
    parts: list[str] = []

    # 1. Scene anchor
    style = project.style_mood or "cinematic"
    parts.append(f"{shot.description.rstrip('.')} in a {style} style.")

    # 2. Subject from project key message
    if project.key_message:
        parts.append(project.key_message.rstrip(".") + ".")

    # 3. Lighting
    if shot.lighting:
        parts.append(shot.lighting.rstrip(".") + ".")

    # 4. Audio — woven into the narrative, not prefixed
    if shot.audio:
        # Transform "Audio: X" or bare audio into natural prose
        audio_text = shot.audio.strip()
        # Strip any existing "Audio:" prefix for clean weaving
        for prefix in ("Audio:", "Sound:", "SFX:"):
            if audio_text.lower().startswith(prefix.lower()):
                audio_text = audio_text[len(prefix):].strip()
        # Weave as ambient description
        if audio_text:
            # Lowercase first char to flow as continuation
            if audio_text[0].isupper():
                audio_text = audio_text[0].lower() + audio_text[1:]
            parts.append(f"The sound of {audio_text.rstrip('.')}.")

    # 5. Camera — skip when LoRA is set (LoRA handles camera)
    lora_name = CAMERA_LORA_MAP.get(shot.camera_movement, "")
    if not lora_name and shot.camera_movement != "static":
        camera_desc = shot.camera_movement.replace("_", " ")
        parts.append(f"The camera {camera_desc}s smoothly.")

    # 6. "Over time, ..." suffix for gradual scene evolution on longer clips
    if shot.duration > 5.0:
        parts.append("Over time, the scene subtly evolves.")

    prompt = " ".join(parts)

    # Select negative prompt from preset or default
    preset = LTX_PRESETS.get(content_type, {})
    neg_key = str(preset.get("neg", "standard"))
    negative_prompt = NEGATIVE_PROMPTS.get(neg_key, NEGATIVE_PROMPTS["standard"])

    return ToolPrompt(
        prompt=prompt,
        negative_prompt=negative_prompt,
        lora_name=lora_name,
        lora_strength=shot.camera_strength,
    )
