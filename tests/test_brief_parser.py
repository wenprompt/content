"""Tests for brief_parser, prompt_generator, and the /plan endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models import Project
from backend.pipeline.brief_parser import (
    MAX_DURATION_PER_TOOL,
    ShotPlan,
    _postprocess,
    parse_brief,
)
from backend.pipeline.prompt_generator import (
    CAMERA_LORA_MAP,
    generate_tool_prompt,
)


def _make_project(**overrides: object) -> Project:
    defaults: dict[str, object] = {
        "name": "Test Product",
        "description": "A sleek wireless earbuds product ad",
        "content_type": "product_ad",
        "target_platform": "tiktok",
        "style_mood": "modern minimalist",
        "duration_target": 30,
        "audio_needs": "upbeat electronic",
        "key_message": "Crystal clear sound anywhere",
        "tool_preference": "auto",
        "budget_limit": 20.0,
        "reference_images": "[]",
        "status": "draft",
    }
    defaults.update(overrides)
    return Project(**defaults)


def _make_raw_shots(count: int = 6, tool: str = "ltx") -> list[dict[str, object]]:
    return [
        {
            "name": f"Shot {i + 1}",
            "order_index": i,
            "shot_type": "image_to_video",
            "tool": tool,
            "description": f"Scene {i + 1} description",
            "camera_movement": "dolly_in" if i % 2 == 0 else "static",
            "camera_strength": 0.85,
            "duration": 5.0,
            "transition_type": "hard_cut" if i == 0 else "last_frame",
            "lighting": "soft studio lighting",
            "audio": "ambient music",
        }
        for i in range(count)
    ]


def _make_shot_plan(tool: str = "ltx", **overrides: object) -> ShotPlan:
    defaults: dict[str, object] = {
        "name": "Test Shot",
        "order_index": 0,
        "shot_type": "image_to_video",
        "tool": tool,
        "description": "A product floating in mid-air with particles swirling around it",
        "camera_movement": "dolly_in",
        "camera_strength": 0.85,
        "duration": 5.0,
        "width": 1080,
        "height": 1920,
        "transition_type": "hard_cut",
        "lighting": "warm golden hour backlight",
        "audio": "upbeat electronic music",
    }
    defaults.update(overrides)
    return ShotPlan(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestParseBrief
# ---------------------------------------------------------------------------


class TestParseBrief:
    def test_product_ad_generates_correct_shot_count(self) -> None:
        project = _make_project(content_type="product_ad")
        raw = _make_raw_shots(6)
        plans = _postprocess(raw, project)
        assert len(plans) == 6

    def test_short_clip_tiktok_dimensions(self) -> None:
        project = _make_project(target_platform="tiktok")
        raw = _make_raw_shots(3)
        plans = _postprocess(raw, project)
        for plan in plans:
            assert plan.width == 768
            assert plan.height == 1344

    def test_youtube_dimensions(self) -> None:
        project = _make_project(target_platform="youtube")
        raw = _make_raw_shots(2)
        plans = _postprocess(raw, project)
        for plan in plans:
            assert plan.width == 1280
            assert plan.height == 720

    def test_tool_preference_override_ltx(self) -> None:
        project = _make_project(tool_preference="ltx")
        raw = _make_raw_shots(3, tool="veo")
        plans = _postprocess(raw, project)
        for plan in plans:
            assert plan.tool == "ltx"

    def test_auto_tool_selection_preserves_original(self) -> None:
        project = _make_project(tool_preference="auto")
        raw = _make_raw_shots(2, tool="veo")
        plans = _postprocess(raw, project)
        for plan in plans:
            assert plan.tool == "veo"

    def test_duration_clamping_per_tool(self) -> None:
        project = _make_project(tool_preference="auto")
        raw = _make_raw_shots(1, tool="veo")
        raw[0]["duration"] = 15.0  # exceeds veo max of 8s
        plans = _postprocess(raw, project)
        assert plans[0].duration == MAX_DURATION_PER_TOOL["veo"]

    def test_transitions_first_shot_hard_cut(self) -> None:
        project = _make_project()
        raw = _make_raw_shots(3)
        raw[0]["transition_type"] = "last_frame"  # should be overridden
        plans = _postprocess(raw, project)
        assert plans[0].transition_type == "hard_cut"
        assert plans[1].transition_type == "last_frame"

    def test_missing_api_key_raises(self) -> None:
        project = _make_project()
        with pytest.raises(ValueError, match="API key is required"):
            import asyncio

            asyncio.get_event_loop().run_until_complete(
                parse_brief(project, api_key="")
            )

    @patch("backend.pipeline.brief_parser._call_gemini")
    async def test_parse_brief_calls_gemini(self, mock_gemini: AsyncMock) -> None:
        mock_gemini.return_value = _make_raw_shots(3)
        project = _make_project()
        plans = await parse_brief(project, provider="gemini", api_key="test-key")
        assert len(plans) == 3
        mock_gemini.assert_called_once()

    @patch("backend.pipeline.brief_parser._call_openai")
    async def test_parse_brief_calls_openai(self, mock_openai: AsyncMock) -> None:
        mock_openai.return_value = _make_raw_shots(4)
        project = _make_project()
        plans = await parse_brief(
            project, provider="openai", api_key="test-key", model="gpt-5.2"
        )
        assert len(plans) == 4
        mock_openai.assert_called_once()


# ---------------------------------------------------------------------------
# TestGenerateToolPrompt
# ---------------------------------------------------------------------------


class TestGenerateToolPrompt:
    def test_ltx_prompt_flowing_paragraph(self) -> None:
        plan = _make_shot_plan(tool="ltx")
        project = _make_project()
        result = generate_tool_prompt(plan, project)
        # Should be a flowing paragraph, not bullet points
        assert "\n-" not in result.prompt
        assert "floating in mid-air" in result.prompt

    def test_ltx_negative_prompt_set(self) -> None:
        plan = _make_shot_plan(tool="ltx")
        project = _make_project()
        result = generate_tool_prompt(plan, project)
        # New prompter uses content-type-based negative prompts; default is "standard"
        assert "worst quality" in result.negative_prompt
        assert "low quality" in result.negative_prompt

    def test_ltx_lora_mapping(self) -> None:
        plan = _make_shot_plan(tool="ltx", camera_movement="dolly_in")
        project = _make_project()
        result = generate_tool_prompt(plan, project)
        assert result.lora_name == CAMERA_LORA_MAP["dolly_in"]

    def test_ltx_no_camera_words_with_lora(self) -> None:
        plan = _make_shot_plan(tool="ltx", camera_movement="dolly_in")
        project = _make_project()
        result = generate_tool_prompt(plan, project)
        # When LoRA is set, camera movement text should not be in prompt
        assert "Camera:" not in result.prompt

    def test_ltx_camera_words_without_lora(self) -> None:
        plan = _make_shot_plan(tool="ltx", camera_movement="crane_up")
        project = _make_project()
        result = generate_tool_prompt(plan, project)
        # Unknown camera movement → no LoRA, camera text in prompt
        assert result.lora_name == ""
        assert "camera" in result.prompt.lower()

    def test_veo_prompt_includes_audio(self) -> None:
        plan = _make_shot_plan(tool="veo", audio="dramatic orchestral swell")
        project = _make_project()
        result = generate_tool_prompt(plan, project)
        assert "dramatic orchestral swell" in result.prompt

    def test_veo_no_negative_prompt(self) -> None:
        plan = _make_shot_plan(tool="veo")
        project = _make_project()
        result = generate_tool_prompt(plan, project)
        assert result.negative_prompt == ""

    def test_veo_no_lora(self) -> None:
        plan = _make_shot_plan(tool="veo")
        project = _make_project()
        result = generate_tool_prompt(plan, project)
        assert result.lora_name == ""

    def test_sora_has_visual_and_audio_sections(self) -> None:
        plan = _make_shot_plan(tool="sora")
        project = _make_project()
        result = generate_tool_prompt(plan, project)
        assert "[VISUAL DESCRIPTION]" in result.prompt
        assert "[AUDIO]" in result.prompt

    def test_sora_no_lora(self) -> None:
        plan = _make_shot_plan(tool="sora")
        project = _make_project()
        result = generate_tool_prompt(plan, project)
        assert result.lora_name == ""
        assert result.lora_strength == 0.0


# ---------------------------------------------------------------------------
# TestPlanEndpoint
# ---------------------------------------------------------------------------


class TestPlanEndpoint:
    @patch("backend.api.projects.parse_brief")
    async def test_plan_creates_shots(
        self, mock_parse: AsyncMock, client: MagicMock
    ) -> None:
        mock_parse.return_value = [
            _make_shot_plan(tool="ltx"),
            _make_shot_plan(tool="ltx", order_index=1, name="Shot 2"),
        ]
        # Create project
        resp = await client.post(
            "/api/projects",
            json={"name": "Test", "description": "A cool product video"},
        )
        project_id = resp.json()["id"]

        with patch("backend.api.projects.get_settings") as mock_settings:
            s = MagicMock()
            s.brief_parser_provider = "gemini"
            s.gemini_api_key = "test-key"
            s.brief_parser_model = "gemini-2.5-flash"
            mock_settings.return_value = s

            resp = await client.post(f"/api/projects/{project_id}/plan")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "planned"
        assert len(data["shots"]) == 2

    @patch("backend.api.projects.parse_brief")
    async def test_plan_replaces_existing_shots(
        self, mock_parse: AsyncMock, client: MagicMock
    ) -> None:
        mock_parse.return_value = [_make_shot_plan(tool="ltx")]

        resp = await client.post(
            "/api/projects",
            json={"name": "Test", "description": "A product video"},
        )
        project_id = resp.json()["id"]

        # Create an existing shot
        await client.post(
            f"/api/projects/{project_id}/shots",
            json={"name": "Old Shot", "prompt": "old prompt"},
        )

        with patch("backend.api.projects.get_settings") as mock_settings:
            s = MagicMock()
            s.brief_parser_provider = "gemini"
            s.gemini_api_key = "test-key"
            s.brief_parser_model = "gemini-2.5-flash"
            mock_settings.return_value = s

            resp = await client.post(f"/api/projects/{project_id}/plan")

        data = resp.json()
        assert len(data["shots"]) == 1
        assert data["shots"][0]["name"] == "Test Shot"

    @patch("backend.api.projects.parse_brief")
    async def test_plan_sets_status_planned(
        self, mock_parse: AsyncMock, client: MagicMock
    ) -> None:
        mock_parse.return_value = [_make_shot_plan()]

        resp = await client.post(
            "/api/projects",
            json={"name": "Test", "description": "Product video"},
        )
        project_id = resp.json()["id"]

        with patch("backend.api.projects.get_settings") as mock_settings:
            s = MagicMock()
            s.brief_parser_provider = "gemini"
            s.gemini_api_key = "key"
            s.brief_parser_model = "gemini-2.5-flash"
            mock_settings.return_value = s

            resp = await client.post(f"/api/projects/{project_id}/plan")

        assert resp.json()["status"] == "planned"

    async def test_plan_project_not_found(self, client: MagicMock) -> None:
        resp = await client.post("/api/projects/nonexistent/plan")
        assert resp.status_code == 404

    async def test_plan_empty_description(self, client: MagicMock) -> None:
        resp = await client.post(
            "/api/projects", json={"name": "Test", "description": ""}
        )
        project_id = resp.json()["id"]

        with patch("backend.api.projects.get_settings") as mock_settings:
            s = MagicMock()
            s.brief_parser_provider = "gemini"
            s.gemini_api_key = "key"
            s.brief_parser_model = "gemini-2.5-flash"
            mock_settings.return_value = s

            resp = await client.post(f"/api/projects/{project_id}/plan")

        assert resp.status_code == 400
        assert "description" in resp.json()["detail"].lower()

    async def test_plan_no_api_key(self, client: MagicMock) -> None:
        resp = await client.post(
            "/api/projects",
            json={"name": "Test", "description": "A product video"},
        )
        project_id = resp.json()["id"]

        with patch("backend.api.projects.get_settings") as mock_settings:
            s = MagicMock()
            s.brief_parser_provider = "gemini"
            s.gemini_api_key = ""
            s.brief_parser_model = "gemini-2.5-flash"
            mock_settings.return_value = s

            resp = await client.post(f"/api/projects/{project_id}/plan")

        assert resp.status_code == 400
        assert "api key" in resp.json()["detail"].lower()
