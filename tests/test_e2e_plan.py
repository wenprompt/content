"""E2E integration test: plan project via Gemini -> generate videos via LTX I2V chain.

Requires: running FastAPI server (port 8000), ComfyUI (port 8188), and valid Gemini API key.
Run with: uv run pytest -m integration tests/test_e2e_plan.py -v -s
"""

from pathlib import Path

import httpx
import pytest

BASE = "http://localhost:8000"

pytestmark = pytest.mark.integration


@pytest.fixture
async def api() -> httpx.AsyncClient:
    async with httpx.AsyncClient(base_url=BASE, timeout=600) as c:
        r = await c.get("/health")
        if r.status_code != 200:
            pytest.skip("FastAPI server not running on port 8000")
        yield c


class TestPlanAndGenerate:
    async def test_plan_generates_i2v_shots(self, api: httpx.AsyncClient) -> None:
        """Plan a project and verify Gemini returns I2V shots with correct structure."""
        project = (await api.post("/api/projects", json={
            "name": "E2E Test Product",
            "description": "Sleek wireless earbuds with minimalist charging case, premium product b-roll",
            "content_type": "b_roll",
            "target_platform": "tiktok",
            "style_mood": "cinematic, moody",
            "duration_target": 10,
            "tool_preference": "ltx",
        })).json()
        pid = project["id"]

        r = await api.post(f"/api/projects/{pid}/plan")
        assert r.status_code == 200

        data = r.json()
        assert data["status"] == "planned"
        assert len(data["shots"]) >= 3

        for shot in data["shots"]:
            assert shot["shot_type"] == "image_to_video"
            assert shot["width"] == 768
            assert shot["height"] == 1344
            assert shot["negative_prompt"] != ""
            assert shot["prompt"] != ""

        # First shot must be hard_cut
        assert data["shots"][0]["transition_type"] == "hard_cut"

    async def test_full_pipeline_with_i2v_chaining(self, api: httpx.AsyncClient) -> None:
        """Full pipeline: plan -> generate with Nano Banana ref image + last-frame chaining."""
        project = (await api.post("/api/projects", json={
            "name": "E2E Full Pipeline",
            "description": "Premium wireless earbuds product b-roll with dramatic lighting",
            "content_type": "b_roll",
            "target_platform": "tiktok",
            "style_mood": "cinematic, moody, premium",
            "duration_target": 10,
            "tool_preference": "ltx",
        })).json()
        pid = project["id"]

        # Plan
        r = await api.post(f"/api/projects/{pid}/plan")
        assert r.status_code == 200
        shots = r.json()["shots"]

        # Generate
        r = await api.post(f"/api/projects/{pid}/generate")
        assert r.status_code == 201
        job_id = r.json()["id"]

        # Poll until done
        import asyncio

        for _ in range(120):  # 20 min max
            await asyncio.sleep(10)
            j = (await api.get(f"/api/jobs/{job_id}")).json()
            if j["status"] in ("completed", "failed", "cancelled"):
                break

        assert j["status"] == "completed", f"Job failed: {j.get('error')}"
        assert j["output_path"] != ""

        # Verify output files
        output_dir = Path("output") / pid
        shots_dir = output_dir / "shots"
        refs_dir = output_dir / "references"

        # All shots generated
        for i in range(len(shots)):
            assert (shots_dir / f"shot_{i:02d}.mp4").exists()

        # Reference image for first shot (Nano Banana)
        assert (refs_dir / "ref_00.png").exists()

        # Last frames extracted for chaining (shots 1+)
        for i in range(1, len(shots)):
            assert (refs_dir / f"lastframe_{i:02d}.png").exists()

        # Final concatenated video
        final = Path(j["output_path"])
        assert final.exists()
        assert final.stat().st_size > 0
