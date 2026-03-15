"""Tests for trend intelligence prompt enhancer."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from backend.pipeline.prompt_generator import CAMERA_LORA_MAP
from backend.trend_intelligence.prompt_enhancer import (
    _normalize_camera_movement,
    create_shot_plans_from_analysis,
    generate_prompts,
)

SAMPLE_ANALYSIS: dict[str, Any] = {
    "hook_analysis": {
        "visual_element": "product close-up",
        "camera_angle": "low angle",
        "timing_seconds": 1.5,
    },
    "visual_style": {
        "color_palette": ["#FF5733", "#33FF57"],
        "lighting": "warm golden hour backlight",
        "aesthetic": "modern minimalist",
    },
    "camera_work": {
        "shot_types": ["close-up", "wide"],
        "movements": ["dolly_in", "static"],
        "transitions": ["cut"],
        "avg_shot_duration": 3.5,
    },
    "pacing": {
        "tempo": "fast",
        "energy_curve": "builds",
        "number_of_cuts": 4,
        "total_duration": 15.0,
    },
    "audio": {
        "music_genre": "electronic",
        "music_tempo_bpm": 128,
        "sound_effects": ["whoosh"],
        "audio_visual_sync": "tight",
    },
    "content_structure": {
        "pattern": "hook-setup-payoff",
        "format_type": "showcase",
    },
    "product_presentation": {
        "appearance_method": "hero reveal",
        "features_highlighted": ["design"],
    },
    "engagement_drivers": {
        "shareability_factor": "satisfying reveal",
        "emotional_trigger": "curiosity",
        "cta": "link in bio",
    },
    "shot_breakdown": [
        {
            "timestamp": "0:00-0:03",
            "description": "Hook shot with dramatic close-up",
            "camera_movement": "dolly_in",
            "duration_sec": 3.0,
        },
        {
            "timestamp": "0:03-0:07",
            "description": "Product reveal wide angle",
            "camera_movement": "static",
            "duration_sec": 4.0,
        },
        {
            "timestamp": "0:07-0:12",
            "description": "Features showcase panning",
            "camera_movement": "pan_left",
            "duration_sec": 5.0,
        },
    ],
}


def _make_project(**overrides: Any) -> Any:
    defaults = {
        "id": "proj-1",
        "name": "Test Project",
        "description": "A test project",
        "content_type": "product_ad",
        "target_platform": "tiktok",
        "style_mood": "modern cinematic",
        "duration_target": 15,
        "audio_needs": "upbeat music",
        "key_message": "Best product ever",
        "tool_preference": "ltx",
        "budget_limit": 20.0,
        "reference_images": "[]",
        "status": "draft",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestNormalizeCameraMovement:
    def test_direct_mapping(self) -> None:
        assert _normalize_camera_movement("dolly_in") == "dolly_in"
        assert _normalize_camera_movement("static") == "static"
        assert _normalize_camera_movement("jib_up") == "jib_up"

    def test_alias_mapping(self) -> None:
        assert _normalize_camera_movement("zoom_in") == "dolly_in"
        assert _normalize_camera_movement("pan_left") == "dolly_left"
        assert _normalize_camera_movement("tilt_up") == "jib_up"
        assert _normalize_camera_movement("crane_down") == "jib_down"
        assert _normalize_camera_movement("pull_out") == "dolly_out"

    def test_unknown_defaults_to_static(self) -> None:
        assert _normalize_camera_movement("helicopter_spin") == "static"
        assert _normalize_camera_movement("unknown") == "static"

    def test_case_insensitive(self) -> None:
        assert _normalize_camera_movement("DOLLY_IN") == "dolly_in"
        assert _normalize_camera_movement("Pan Left") == "dolly_left"


class TestCreateShotPlans:
    def test_creates_correct_shot_count(self) -> None:
        project = _make_project()
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)

        assert len(plans) == 3

    def test_maps_camera_movements_to_lora(self) -> None:
        project = _make_project()
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)

        # dolly_in should map to LoRA
        assert plans[0].camera_movement == "dolly_in"
        assert plans[0].camera_movement in CAMERA_LORA_MAP

        # static should map to LoRA
        assert plans[1].camera_movement == "static"

        # pan_left → dolly_left
        assert plans[2].camera_movement == "dolly_left"

    def test_durations_match_analysis(self) -> None:
        project = _make_project()
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)

        assert plans[0].duration == 3.0
        assert plans[1].duration == 4.0
        assert plans[2].duration == 5.0

    def test_first_shot_hard_cut(self) -> None:
        project = _make_project()
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)

        # First shot always hard_cut; others default to hard_cut when not specified
        assert plans[0].transition_type == "hard_cut"
        assert plans[1].transition_type == "hard_cut"
        assert plans[2].transition_type == "hard_cut"

    def test_respects_per_shot_transition_type(self) -> None:
        """When shots have explicit transition_type, it's respected."""
        analysis = dict(SAMPLE_ANALYSIS)
        analysis["shot_breakdown"] = [
            {"description": "A", "camera_movement": "static", "duration_sec": 3},
            {"description": "B", "camera_movement": "static", "duration_sec": 4, "transition_type": "last_frame"},
            {"description": "C", "camera_movement": "static", "duration_sec": 5, "transition_type": "hard_cut"},
        ]
        project = _make_project()
        plans = create_shot_plans_from_analysis(analysis, project)

        assert plans[0].transition_type == "hard_cut"  # always hard_cut for first
        assert plans[1].transition_type == "last_frame"
        assert plans[2].transition_type == "hard_cut"

    def test_explicit_tool_preference_respected(self) -> None:
        project = _make_project(tool_preference="ltx")
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)

        for plan in plans:
            assert plan.tool == "ltx"

    def test_auto_tool_defaults_to_veo(self) -> None:
        project = _make_project(tool_preference="auto")
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)

        # No sora signals in SAMPLE_ANALYSIS, so all shots default to veo
        for plan in plans:
            assert plan.tool == "veo"

    def test_auto_tool_routes_sora_for_animation(self) -> None:
        analysis = {
            **SAMPLE_ANALYSIS,
            "shot_breakdown": [
                {"description": "3D Pixar cartoon character appears", "camera_movement": "static", "duration_sec": 5.0},
            ],
        }
        project = _make_project(tool_preference="auto")
        plans = create_shot_plans_from_analysis(analysis, project)

        assert plans[0].tool == "sora"
        assert plans[0].shot_type == "text_to_video"

    def test_auto_tool_routes_sora_for_b_roll(self) -> None:
        analysis = {
            **SAMPLE_ANALYSIS,
            "content_structure": {"format_type": "b_roll"},
            "shot_breakdown": [
                {"description": "sweeping aerial view of mountains", "camera_movement": "dolly_right", "duration_sec": 5.0},
            ],
        }
        project = _make_project(tool_preference="auto")
        plans = create_shot_plans_from_analysis(analysis, project)

        assert plans[0].tool == "sora"

    def test_auto_tool_veo_for_b_roll_with_characters(self) -> None:
        analysis = {
            **SAMPLE_ANALYSIS,
            "content_structure": {"format_type": "b_roll"},
            "shot_breakdown": [
                {"description": "a woman walks through a garden", "camera_movement": "static", "duration_sec": 5.0},
            ],
        }
        project = _make_project(tool_preference="auto")
        plans = create_shot_plans_from_analysis(analysis, project)

        assert plans[0].tool == "veo"

    def test_veo_shot_uses_image_to_video(self) -> None:
        project = _make_project(tool_preference="auto")
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)

        for plan in plans:
            assert plan.shot_type == "image_to_video"

    def test_platform_dimensions(self) -> None:
        project = _make_project(target_platform="tiktok")
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)

        assert plans[0].width == 768
        assert plans[0].height == 1344

    def test_lighting_from_analysis(self) -> None:
        project = _make_project()
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)

        assert plans[0].lighting == "warm golden hour backlight"

    def test_audio_from_analysis(self) -> None:
        project = _make_project()
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)

        assert "electronic" in plans[0].audio
        assert "128" in plans[0].audio

    def test_fallback_when_no_shot_breakdown(self) -> None:
        analysis = {
            "content_structure": {"pattern": "hook-setup-payoff"},
            "pacing": {"total_duration": 10.0},
        }
        project = _make_project()
        plans = create_shot_plans_from_analysis(analysis, project)

        assert len(plans) == 1
        assert plans[0].duration == 10.0

    def test_duration_clamped_to_max(self) -> None:
        analysis = {
            "shot_breakdown": [{
                "description": "Very long shot",
                "camera_movement": "static",
                "duration_sec": 60.0,
            }],
        }
        project = _make_project()
        plans = create_shot_plans_from_analysis(analysis, project)

        assert plans[0].duration == 20.0  # LTX max

    def test_duration_minimum_2_seconds(self) -> None:
        analysis = {
            "shot_breakdown": [{
                "description": "Tiny shot",
                "camera_movement": "static",
                "duration_sec": 0.5,
            }],
        }
        project = _make_project()
        plans = create_shot_plans_from_analysis(analysis, project)

        assert plans[0].duration == 2.0

    def test_missing_optional_fields(self) -> None:
        """Test with minimal analysis dict — missing most optional fields."""
        analysis: dict[str, Any] = {
            "shot_breakdown": [{
                "description": "Basic shot",
            }],
        }
        project = _make_project()
        plans = create_shot_plans_from_analysis(analysis, project)

        assert len(plans) == 1
        assert plans[0].camera_movement == "static"
        assert plans[0].duration == 5.0  # default
        assert plans[0].lighting == ""  # no visual_style


class TestGeneratePrompts:
    def test_generates_prompts_for_all_shots(self) -> None:
        project = _make_project()
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)
        enriched = generate_prompts(plans, project)

        assert len(enriched) == len(plans)

    def test_preserves_shot_plan_fields(self) -> None:
        project = _make_project()
        plans = create_shot_plans_from_analysis(SAMPLE_ANALYSIS, project)
        enriched = generate_prompts(plans, project)

        for original, result in zip(plans, enriched, strict=True):
            assert result.name == original.name
            assert result.tool == original.tool
            assert result.duration == original.duration
            assert result.camera_movement == original.camera_movement
