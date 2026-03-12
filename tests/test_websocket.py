from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from backend.api.websocket import ConnectionManager
from backend.main import app


@pytest.fixture
def manager() -> ConnectionManager:
    return ConnectionManager()


class TestConnectionManager:
    async def test_connect(self, manager: ConnectionManager) -> None:
        ws = AsyncMock()
        await manager.connect("c1", ws)
        assert "c1" in manager.active_connections
        ws.accept.assert_awaited_once()

    async def test_disconnect(self, manager: ConnectionManager) -> None:
        ws = AsyncMock()
        await manager.connect("c1", ws)
        manager.disconnect("c1")
        assert "c1" not in manager.active_connections

    async def test_disconnect_nonexistent(self, manager: ConnectionManager) -> None:
        manager.disconnect("nope")  # should not raise

    async def test_broadcast(self, manager: ConnectionManager) -> None:
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect("c1", ws1)
        await manager.connect("c2", ws2)

        msg = {"type": "test", "data": 42}
        await manager.broadcast(msg)

        ws1.send_json.assert_awaited_once_with(msg)
        ws2.send_json.assert_awaited_once_with(msg)

    async def test_broadcast_removes_disconnected(self, manager: ConnectionManager) -> None:
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_json.side_effect = RuntimeError("disconnected")
        await manager.connect("good", ws_good)
        await manager.connect("bad", ws_bad)

        await manager.broadcast({"type": "test"})

        assert "good" in manager.active_connections
        assert "bad" not in manager.active_connections


class TestWebSocketEndpoint:
    def test_websocket_connect(self, setup_db: None) -> None:
        import asyncio

        app.state.job_queue = asyncio.Queue()
        with TestClient(app) as tc, tc.websocket_connect("/ws/test-client") as ws:
            ws.send_text("ping")

    def test_websocket_receives_progress(self, setup_db: None) -> None:
        """Integration: connect WS, create project+shots, generate, receive progress."""
        import asyncio
        import threading

        from backend.database import get_db
        from tests.conftest import db_session

        async def _override_db():  # type: ignore[no-untyped-def]
            async with db_session() as session:
                yield session

        app.dependency_overrides[get_db] = _override_db
        app.state.job_queue = asyncio.Queue()

        with TestClient(app) as tc, tc.websocket_connect("/ws/integration"):
            # Create project
            resp = tc.post("/api/projects", json={"name": "WS Test"})
            project_id = resp.json()["id"]

            # Add a shot
            tc.post(f"/api/projects/{project_id}/shots", json={"prompt": "test"})

            # Trigger generation
            resp = tc.post(f"/api/projects/{project_id}/generate")
            assert resp.status_code == 201
            job_id = resp.json()["id"]

            # Run the worker in a background thread to process the queued job
            async def _run_worker() -> None:
                from unittest.mock import patch as _patch

                from backend.pipeline.orchestrator import _process_job

                with _patch(
                    "backend.pipeline.orchestrator.async_session", db_session
                ), _patch(
                    "backend.pipeline.orchestrator._generate_shot",
                    new_callable=AsyncMock,
                    return_value=None,
                ), _patch(
                    "backend.pipeline.orchestrator.concatenate_project",
                    new_callable=AsyncMock,
                ):
                    await _process_job(job_id)

            worker_thread = threading.Thread(
                target=lambda: asyncio.run(_run_worker())
            )
            worker_thread.start()
            worker_thread.join(timeout=5)

            # The broadcast went to the real manager; check DB state instead
            from sqlalchemy import select

            from backend.models import Job

            async def _check_job() -> str:
                async with db_session() as s:
                    result = await s.execute(select(Job).where(Job.id == job_id))
                    return result.scalar_one().status

            status = asyncio.run(_check_job())
            assert status == "completed"

        app.dependency_overrides.clear()
