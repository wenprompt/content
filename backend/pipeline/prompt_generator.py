"""Rule-based, deterministic prompt formatting per video generation tool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models import Project
    from backend.pipeline.brief_parser import ShotPlan

CAMERA_LORA_MAP: dict[str, str] = {
    "static": "ltx-2-19b-lora-camera-control-static.safetensors",
    "dolly_in": "ltx-2-19b-lora-camera-control-dolly-in.safetensors",
    "dolly_out": "ltx-2-19b-lora-camera-control-dolly-out.safetensors",
    "dolly_left": "ltx-2-19b-lora-camera-control-dolly-left.safetensors",
    "dolly_right": "ltx-2-19b-lora-camera-control-dolly-right.safetensors",
    "jib_up": "ltx-2-19b-lora-camera-control-jib-up.safetensors",
    "jib_down": "ltx-2-19b-lora-camera-control-jib-down.safetensors",
}

LTX_NEGATIVE_PROMPT = (
    "worst quality, low quality, blurry, pixelated, grainy, distorted, "
    "watermark, text, logo, shaky, glitchy, deformed, disfigured, "
    "morphing, warping, flicker, temporal artifacts, freeze frame"
)


@dataclass
class ToolPrompt:
    prompt: str
    negative_prompt: str
    lora_name: str
    lora_strength: float


def generate_tool_prompt(
    shot_plan: ShotPlan,
    project: Project,
    content_type: str = "",
) -> ToolPrompt:
    """Generate a tool-specific prompt from a ShotPlan and Project.

    When content_type is provided, model-specific prompters use it to select
    optimal presets (resolution, fps, negative prompts, I2V strength).
    Falls back to the ShotPlan's own content_type if not passed explicitly.
    """
    ct = content_type or getattr(shot_plan, "content_type", "")

    if shot_plan.tool == "veo":
        from backend.pipeline.prompters.veo_prompter import build_veo_prompt
        return build_veo_prompt(shot_plan, project, content_type=ct)
    if shot_plan.tool == "sora":
        from backend.pipeline.prompters.sora_prompter import build_sora_prompt
        return build_sora_prompt(shot_plan, project, content_type=ct)

    from backend.pipeline.prompters.ltx_prompter import build_ltx_prompt
    return build_ltx_prompt(shot_plan, project, content_type=ct)
