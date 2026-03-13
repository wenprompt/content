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


def _generate_ltx_prompt(shot_plan: ShotPlan, project: Project) -> ToolPrompt:
    parts: list[str] = []

    # Scene anchor
    style = project.style_mood or "cinematic"
    parts.append(f"{shot_plan.description.rstrip('.')} in a {style} style.")

    # Subject from project
    if project.key_message:
        parts.append(project.key_message.rstrip(".") + ".")

    # Lighting
    if shot_plan.lighting:
        parts.append(shot_plan.lighting.rstrip(".") + ".")

    # Audio (LTX doesn't use audio natively, but include for context)
    if shot_plan.audio:
        parts.append(f"Audio atmosphere: {shot_plan.audio.rstrip('.')}.")

    # Camera — skip when LoRA is set (LoRA handles camera)
    lora_name = CAMERA_LORA_MAP.get(shot_plan.camera_movement, "")
    if not lora_name and shot_plan.camera_movement != "static":
        parts.append(f"Camera: {shot_plan.camera_movement.replace('_', ' ')}.")

    prompt = " ".join(parts)

    return ToolPrompt(
        prompt=prompt,
        negative_prompt=LTX_NEGATIVE_PROMPT,
        lora_name=lora_name,
        lora_strength=shot_plan.camera_strength,
    )


def _generate_veo_prompt(shot_plan: ShotPlan, project: Project) -> ToolPrompt:
    parts: list[str] = []

    # Camera work
    camera = shot_plan.camera_movement.replace("_", " ")
    parts.append(f"A {camera} shot.")

    # Subject and action
    parts.append(shot_plan.description.rstrip(".") + ".")

    # Setting
    style = project.style_mood or "cinematic"
    parts.append(f"The mood is {style}.")

    # Lighting
    if shot_plan.lighting:
        parts.append(shot_plan.lighting.rstrip(".") + ".")

    # Audio (Veo 3.1 supports native audio)
    if shot_plan.audio:
        parts.append(f"Sound: {shot_plan.audio.rstrip('.')}.")

    prompt = " ".join(parts)

    return ToolPrompt(
        prompt=prompt,
        negative_prompt="",
        lora_name="",
        lora_strength=0.0,
    )


def _generate_sora_prompt(shot_plan: ShotPlan, project: Project) -> ToolPrompt:
    parts: list[str] = []

    # Visual description section
    parts.append("[VISUAL DESCRIPTION]")
    style = project.style_mood or "cinematic"
    parts.append(f"Style: {style}.")
    parts.append(shot_plan.description.rstrip(".") + ".")
    if shot_plan.lighting:
        parts.append(f"Lighting: {shot_plan.lighting.rstrip('.')}.")
    camera = shot_plan.camera_movement.replace("_", " ")
    parts.append(f"Camera: {camera}.")

    # Audio section
    parts.append("[AUDIO]")
    if shot_plan.audio:
        parts.append(shot_plan.audio.rstrip(".") + ".")
    else:
        parts.append("Ambient sound.")

    prompt = " ".join(parts)

    return ToolPrompt(
        prompt=prompt,
        negative_prompt="",
        lora_name="",
        lora_strength=0.0,
    )


def generate_tool_prompt(shot_plan: ShotPlan, project: Project) -> ToolPrompt:
    """Generate a tool-specific prompt from a ShotPlan and Project."""
    if shot_plan.tool == "veo":
        return _generate_veo_prompt(shot_plan, project)
    if shot_plan.tool == "sora":
        return _generate_sora_prompt(shot_plan, project)
    return _generate_ltx_prompt(shot_plan, project)
