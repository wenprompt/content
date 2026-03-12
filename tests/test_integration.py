"""End-to-end integration tests exercising every API endpoint and its intended behaviour.

Each test class groups related endpoints. Tests within a class are independent
(autouse setup_db fixture resets the DB between tests).
"""

import asyncio
import json
import threading
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from starlette.testclient import TestClient

from backend.database import get_db
from backend.main import app
from backend.models import Job, Shot
from tests.conftest import db_session

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Projects CRUD
# ---------------------------------------------------------------------------


class TestProjectsCRUD:
    async def test_create_with_defaults(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "My Project"})
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "My Project"
        assert data["status"] == "draft"
        assert data["content_type"] == "short_clip"
        assert data["target_platform"] == "tiktok"
        assert data["budget_limit"] == 20.0
        assert data["shots"] == []
        assert data["id"]
        assert data["created_at"]
        assert data["updated_at"]

    async def test_create_with_all_fields(self, client: AsyncClient) -> None:
        payload = {
            "name": "Full Project",
            "description": "Detailed desc",
            "content_type": "product_ad",
            "target_platform": "instagram",
            "style_mood": "cinematic",
            "duration_target": 30,
            "audio_needs": "background music",
            "key_message": "Buy now",
            "tool_preference": "ltx",
            "budget_limit": 50.0,
        }
        r = await client.post("/api/projects", json=payload)
        assert r.status_code == 201
        data = r.json()
        for key, value in payload.items():
            assert data[key] == value

    async def test_list_empty(self, client: AsyncClient) -> None:
        r = await client.get("/api/projects")
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_returns_multiple(self, client: AsyncClient) -> None:
        await client.post("/api/projects", json={"name": "First"})
        await client.post("/api/projects", json={"name": "Second"})
        r = await client.get("/api/projects")
        assert r.status_code == 200
        names = {p["name"] for p in r.json()}
        assert names == {"First", "Second"}

    async def test_get_includes_shots(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        await client.post(f"/api/projects/{pid}/shots", json={"name": "S1"})
        r = await client.get(f"/api/projects/{pid}")
        assert len(r.json()["shots"]) == 1
        assert r.json()["shots"][0]["name"] == "S1"

    async def test_get_not_found(self, client: AsyncClient) -> None:
        r = await client.get("/api/projects/does-not-exist")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    async def test_update_partial(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "Old", "description": "Keep"})
        pid = r.json()["id"]
        r = await client.put(f"/api/projects/{pid}", json={"name": "New"})
        assert r.status_code == 200
        assert r.json()["name"] == "New"
        assert r.json()["description"] == "Keep"  # unchanged

    async def test_update_not_found(self, client: AsyncClient) -> None:
        r = await client.put("/api/projects/nope", json={"name": "X"})
        assert r.status_code == 404

    async def test_delete(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.delete(f"/api/projects/{pid}")
        assert r.status_code == 204
        r = await client.get(f"/api/projects/{pid}")
        assert r.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient) -> None:
        r = await client.delete("/api/projects/nope")
        assert r.status_code == 404

    async def test_delete_cascades_shots_and_jobs(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        await client.post(f"/api/projects/{pid}/shots", json={"name": "S1"})
        await client.post(f"/api/projects/{pid}/generate")

        r = await client.delete(f"/api/projects/{pid}")
        assert r.status_code == 204

        # Verify shots and jobs are gone at DB level
        async with db_session() as s:
            shots = (await s.execute(select(Shot).where(Shot.project_id == pid))).scalars().all()
            jobs = (await s.execute(select(Job).where(Job.project_id == pid))).scalars().all()
            assert len(list(shots)) == 0
            assert len(list(jobs)) == 0


# ---------------------------------------------------------------------------
# Shots CRUD
# ---------------------------------------------------------------------------


class TestShotsCRUD:
    async def test_create_auto_increments_order(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        s0 = await client.post(f"/api/projects/{pid}/shots", json={"name": "A"})
        s1 = await client.post(f"/api/projects/{pid}/shots", json={"name": "B"})
        s2 = await client.post(f"/api/projects/{pid}/shots", json={"name": "C"})
        assert s0.json()["order_index"] == 0
        assert s1.json()["order_index"] == 1
        assert s2.json()["order_index"] == 2

    async def test_create_with_all_fields(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        payload = {
            "name": "Hero Shot",
            "shot_type": "image_to_video",
            "tool": "veo",
            "prompt": "A golden sunrise",
            "negative_prompt": "blurry",
            "duration": 8.0,
            "width": 1280,
            "height": 720,
            "fps": 30,
            "cfg": 4.0,
            "steps": 50,
            "seed": 42,
            "lora_name": "Camera-Control-Dolly-In",
            "lora_strength": 0.85,
            "transition_type": "hard_cut",
            "reference_image": "/path/to/ref.png",
        }
        r = await client.post(f"/api/projects/{pid}/shots", json=payload)
        assert r.status_code == 201
        data = r.json()
        for key, value in payload.items():
            assert data[key] == value, f"Mismatch on {key}: {data[key]} != {value}"

    async def test_create_shot_project_not_found(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects/nope/shots", json={"name": "S"})
        assert r.status_code == 404

    async def test_update_shot(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.post(f"/api/projects/{pid}/shots", json={"prompt": "old"})
        sid = r.json()["id"]

        r = await client.put(
            f"/api/projects/{pid}/shots/{sid}",
            json={"prompt": "new prompt", "cfg": 5.0},
        )
        assert r.status_code == 200
        assert r.json()["prompt"] == "new prompt"
        assert r.json()["cfg"] == 5.0
        # Unchanged fields preserved
        assert r.json()["tool"] == "ltx"

    async def test_update_shot_not_found(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.put(f"/api/projects/{pid}/shots/nope", json={"prompt": "x"})
        assert r.status_code == 404

    async def test_delete_shot(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.post(f"/api/projects/{pid}/shots", json={"name": "S"})
        sid = r.json()["id"]

        r = await client.delete(f"/api/projects/{pid}/shots/{sid}")
        assert r.status_code == 204

        # Confirm gone
        r = await client.get(f"/api/projects/{pid}")
        assert len(r.json()["shots"]) == 0

    async def test_delete_shot_not_found(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.delete(f"/api/projects/{pid}/shots/nope")
        assert r.status_code == 404

    async def test_reorder_shots(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        s1 = (await client.post(f"/api/projects/{pid}/shots", json={"name": "A"})).json()
        s2 = (await client.post(f"/api/projects/{pid}/shots", json={"name": "B"})).json()
        s3 = (await client.post(f"/api/projects/{pid}/shots", json={"name": "C"})).json()

        # Reverse order
        r = await client.put(
            f"/api/projects/{pid}/shots/reorder",
            json={"shot_ids": [s3["id"], s2["id"], s1["id"]]},
        )
        assert r.status_code == 200
        result = r.json()
        assert result[0]["id"] == s3["id"]
        assert result[0]["order_index"] == 0
        assert result[1]["id"] == s2["id"]
        assert result[1]["order_index"] == 1
        assert result[2]["id"] == s1["id"]
        assert result[2]["order_index"] == 2

    async def test_reorder_invalid_shot_id(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        await client.post(f"/api/projects/{pid}/shots", json={"name": "S"})
        r = await client.put(
            f"/api/projects/{pid}/shots/reorder",
            json={"shot_ids": ["nonexistent-id"]},
        )
        assert r.status_code == 404

    async def test_reorder_project_not_found(self, client: AsyncClient) -> None:
        r = await client.put(
            "/api/projects/nope/shots/reorder",
            json={"shot_ids": []},
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Jobs & Generation
# ---------------------------------------------------------------------------


class TestJobsAndGeneration:
    async def test_generate_creates_pending_job(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        await client.post(f"/api/projects/{pid}/shots", json={"name": "S1"})
        await client.post(f"/api/projects/{pid}/shots", json={"name": "S2"})

        r = await client.post(f"/api/projects/{pid}/generate")
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "pending"
        assert data["total_shots"] == 2
        assert data["progress"] == 0
        assert data["message"] == "Queued for generation"
        assert data["project_id"] == pid

    async def test_generate_with_no_shots(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.post(f"/api/projects/{pid}/generate")
        assert r.status_code == 201
        assert r.json()["total_shots"] == 0

    async def test_generate_project_not_found(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects/nope/generate")
        assert r.status_code == 404

    async def test_generate_enqueues_job_id(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.post(f"/api/projects/{pid}/generate")
        job_id = r.json()["id"]

        # The job_queue should contain this job_id
        queue = app.state.job_queue
        assert not queue.empty()
        queued_id = queue.get_nowait()
        assert queued_id == job_id

    async def test_get_job(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.post(f"/api/projects/{pid}/generate")
        job_id = r.json()["id"]

        r = await client.get(f"/api/jobs/{job_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == job_id
        assert data["status"] == "pending"
        assert data["created_at"]

    async def test_get_job_not_found(self, client: AsyncClient) -> None:
        r = await client.get("/api/jobs/nonexistent")
        assert r.status_code == 404

    async def test_cancel_job(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.post(f"/api/projects/{pid}/generate")
        job_id = r.json()["id"]

        r = await client.post(f"/api/jobs/{job_id}/cancel")
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

        # Verify persisted
        r = await client.get(f"/api/jobs/{job_id}")
        assert r.json()["status"] == "cancelled"

    async def test_cancel_job_not_found(self, client: AsyncClient) -> None:
        r = await client.post("/api/jobs/nope/cancel")
        assert r.status_code == 404

    async def test_list_jobs_for_project(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        j1 = (await client.post(f"/api/projects/{pid}/generate")).json()
        j2 = (await client.post(f"/api/projects/{pid}/generate")).json()

        r = await client.get(f"/api/projects/{pid}/jobs")
        assert r.status_code == 200
        ids = {j["id"] for j in r.json()}
        assert j1["id"] in ids
        assert j2["id"] in ids
        assert len(r.json()) == 2

    async def test_list_jobs_empty(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.get(f"/api/projects/{pid}/jobs")
        assert r.status_code == 200
        assert r.json() == []

    async def test_multiple_generates_create_separate_jobs(
        self, client: AsyncClient
    ) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        await client.post(f"/api/projects/{pid}/shots", json={"name": "S"})

        j1 = (await client.post(f"/api/projects/{pid}/generate")).json()
        j2 = (await client.post(f"/api/projects/{pid}/generate")).json()
        assert j1["id"] != j2["id"]
        assert j1["total_shots"] == j2["total_shots"] == 1


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class TestUpload:
    async def test_upload_reference_image(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]

        r = await client.post(
            f"/api/projects/{pid}/upload",
            files={"file": ("test.png", b"fake-png-content", "image/png")},
        )
        assert r.status_code == 200
        images = json.loads(r.json()["reference_images"])
        assert len(images) == 1
        assert "test.png" in images[0]

    async def test_upload_multiple_files(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]

        await client.post(
            f"/api/projects/{pid}/upload",
            files={"file": ("a.png", b"data-a", "image/png")},
        )
        r = await client.post(
            f"/api/projects/{pid}/upload",
            files={"file": ("b.png", b"data-b", "image/png")},
        )
        images = json.loads(r.json()["reference_images"])
        assert len(images) == 2

    async def test_upload_project_not_found(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/projects/nope/upload",
            files={"file": ("test.png", b"data", "image/png")},
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


class TestWebSocket:
    def test_websocket_connect_and_keepalive(self, setup_db: None) -> None:
        app.state.job_queue = asyncio.Queue()
        with TestClient(app) as tc, tc.websocket_connect("/ws/client-1") as ws:
            ws.send_text("ping")
            # Connection is alive — no error raised

    def test_websocket_multiple_clients(self, setup_db: None) -> None:
        app.state.job_queue = asyncio.Queue()
        with (
            TestClient(app) as tc,
            tc.websocket_connect("/ws/c1") as ws1,
            tc.websocket_connect("/ws/c2") as ws2,
        ):
            ws1.send_text("hello")
            ws2.send_text("world")


# ---------------------------------------------------------------------------
# End-to-end pipeline: create → shots → generate → worker → completed
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    def test_full_pipeline_job_completes(self, setup_db: None) -> None:
        """Create project, add shots, generate, run worker, verify completion."""

        async def _override_db():  # type: ignore[no-untyped-def]
            async with db_session() as session:
                yield session

        app.dependency_overrides[get_db] = _override_db
        app.state.job_queue = asyncio.Queue()

        with TestClient(app) as tc:
            # Create project with 2 shots
            proj = tc.post("/api/projects", json={"name": "E2E Project"}).json()
            pid = proj["id"]
            tc.post(f"/api/projects/{pid}/shots", json={"name": "Shot A", "prompt": "a"})
            tc.post(f"/api/projects/{pid}/shots", json={"name": "Shot B", "prompt": "b"})

            # Trigger generation
            job = tc.post(f"/api/projects/{pid}/generate").json()
            job_id = job["id"]
            assert job["status"] == "pending"
            assert job["total_shots"] == 2

            # Run the worker
            async def _run_worker() -> None:
                from backend.pipeline.orchestrator import _process_job

                with patch(
                    "backend.pipeline.orchestrator.async_session", db_session
                ), patch(
                    "backend.pipeline.orchestrator._generate_shot",
                    new_callable=AsyncMock,
                    return_value=None,
                ), patch(
                    "backend.pipeline.orchestrator.concatenate_project",
                    new_callable=AsyncMock,
):
                    await _process_job(job_id)

            worker_thread = threading.Thread(
                target=lambda: asyncio.run(_run_worker())
            )
            worker_thread.start()
            worker_thread.join(timeout=5)
            assert not worker_thread.is_alive(), "Worker timed out"

            # Verify job completed via API
            job_resp = tc.get(f"/api/jobs/{job_id}").json()
            assert job_resp["status"] == "completed"
            assert job_resp["progress"] == 100
            assert job_resp["completed_at"] is not None

            # Verify shots completed
            proj_resp = tc.get(f"/api/projects/{pid}").json()
            for shot in proj_resp["shots"]:
                assert shot["status"] == "completed"

            # Verify job appears in project job list
            jobs_list = tc.get(f"/api/projects/{pid}/jobs").json()
            assert any(j["id"] == job_id for j in jobs_list)

        app.dependency_overrides.clear()

    def test_full_pipeline_job_cancelled(self, setup_db: None) -> None:
        """Create, generate, cancel mid-flight, verify partial completion."""

        async def _override_db():  # type: ignore[no-untyped-def]
            async with db_session() as session:
                yield session

        app.dependency_overrides[get_db] = _override_db
        app.state.job_queue = asyncio.Queue()

        with TestClient(app) as tc:
            proj = tc.post("/api/projects", json={"name": "Cancel Test"}).json()
            pid = proj["id"]
            tc.post(f"/api/projects/{pid}/shots", json={"name": "S1"})
            tc.post(f"/api/projects/{pid}/shots", json={"name": "S2"})

            job = tc.post(f"/api/projects/{pid}/generate").json()
            job_id = job["id"]

            # Worker that cancels after first shot
            async def _run_worker() -> None:
                from backend.pipeline.orchestrator import _process_job

                call_count = 0

                async def _cancel_mid(*args: object, **kwargs: object) -> None:
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        async with db_session() as s:
                            result = await s.execute(
                                select(Job).where(Job.id == job_id)
                            )
                            j = result.scalar_one()
                            j.status = "cancelled"
                            await s.commit()

                with patch(
                    "backend.pipeline.orchestrator.async_session", db_session
                ), patch(
                    "backend.pipeline.orchestrator._generate_shot",
                    side_effect=_cancel_mid,
                ), patch(
                    "backend.pipeline.orchestrator.concatenate_project",
                    new_callable=AsyncMock,
                ):
                    await _process_job(job_id)

            worker_thread = threading.Thread(
                target=lambda: asyncio.run(_run_worker())
            )
            worker_thread.start()
            worker_thread.join(timeout=5)

            # First shot completed, second still pending
            proj_resp = tc.get(f"/api/projects/{pid}").json()
            shots = sorted(proj_resp["shots"], key=lambda s: s["order_index"])
            assert shots[0]["status"] == "completed"
            assert shots[1]["status"] == "pending"

        app.dependency_overrides.clear()

    def test_full_pipeline_with_websocket(self, setup_db: None) -> None:
        """Full pipeline with WebSocket connected — verify broadcast messages."""

        async def _override_db():  # type: ignore[no-untyped-def]
            async with db_session() as session:
                yield session

        app.dependency_overrides[get_db] = _override_db
        app.state.job_queue = asyncio.Queue()

        broadcast_messages: list[dict] = []  # type: ignore[type-arg]

        async def _capture_broadcast(message: dict) -> None:  # type: ignore[type-arg]
            broadcast_messages.append(message)
            # Don't call original — no real WS connections in the worker thread

        with TestClient(app) as tc, tc.websocket_connect("/ws/e2e-client"):
            proj = tc.post("/api/projects", json={"name": "WS Pipeline"}).json()
            pid = proj["id"]
            tc.post(f"/api/projects/{pid}/shots", json={"name": "S1"})
            tc.post(f"/api/projects/{pid}/shots", json={"name": "S2"})

            job = tc.post(f"/api/projects/{pid}/generate").json()
            job_id = job["id"]

            async def _run_worker() -> None:
                from backend.pipeline.orchestrator import _process_job

                with patch(
                    "backend.pipeline.orchestrator.async_session", db_session
                ), patch(
                    "backend.pipeline.orchestrator._generate_shot",
                    new_callable=AsyncMock,
                    return_value=None,
                ), patch(
                    "backend.pipeline.orchestrator.concatenate_project",
                    new_callable=AsyncMock,
), patch(
                    "backend.pipeline.orchestrator.manager.broadcast",
                    side_effect=_capture_broadcast,
                ):
                    await _process_job(job_id)

            worker_thread = threading.Thread(
                target=lambda: asyncio.run(_run_worker())
            )
            worker_thread.start()
            worker_thread.join(timeout=5)

            # Verify broadcast message types
            types = [m["type"] for m in broadcast_messages]
            assert "job_progress" in types
            assert types.count("shot_progress") == 2
            assert "job_completed" in types

            # Verify message structure
            for msg in broadcast_messages:
                assert msg["job_id"] == job_id
                assert msg["project_id"] == pid
                assert "progress" in msg
                assert "message" in msg

            # Verify final message
            final = broadcast_messages[-1]
            assert final["type"] == "job_completed"
            assert final["progress"] == 100

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Response schema completeness — ensure all JobResponse fields are present
# ---------------------------------------------------------------------------


class TestResponseSchemas:
    async def test_job_response_has_all_fields(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.post(f"/api/projects/{pid}/generate")
        data = r.json()
        expected_keys = {
            "id", "project_id", "status", "current_shot_index", "total_shots",
            "progress", "message", "error", "output_path", "created_at",
            "completed_at",
        }
        assert expected_keys == set(data.keys())

    async def test_project_response_has_all_fields(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        data = r.json()
        expected_keys = {
            "id", "name", "description", "content_type", "target_platform",
            "style_mood", "duration_target", "audio_needs", "key_message",
            "tool_preference", "budget_limit", "reference_images", "status",
            "created_at", "updated_at", "shots",
        }
        assert expected_keys == set(data.keys())

    async def test_shot_response_has_all_fields(self, client: AsyncClient) -> None:
        r = await client.post("/api/projects", json={"name": "P"})
        pid = r.json()["id"]
        r = await client.post(f"/api/projects/{pid}/shots", json={"name": "S"})
        data = r.json()
        expected_keys = {
            "id", "project_id", "order_index", "name", "shot_type", "tool",
            "prompt", "negative_prompt", "duration", "width", "height", "fps",
            "cfg", "steps", "seed", "lora_name", "lora_strength",
            "transition_type", "reference_image", "output_path", "status",
        }
        assert expected_keys == set(data.keys())
