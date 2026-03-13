from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.clients.base import GenerationResult
from backend.clients.google_client import GoogleAPIError
from backend.models import Job, Project, Shot
from tests.conftest import db_session


async def _create_project_with_shots(
    session: AsyncSession,
    num_shots: int = 2,
    tool: str = "ltx",
    shot_type: str = "text_to_video",
) -> tuple[str, str]:
    """Create a project with shots and a pending job. Returns (project_id, job_id)."""
    project = Project(name="Test Project")
    session.add(project)
    await session.flush()

    for i in range(num_shots):
        shot = Shot(
            project_id=project.id,
            order_index=i,
            name=f"Shot {i}",
            prompt=f"Test prompt {i}",
            tool=tool,
            shot_type=shot_type,
        )
        session.add(shot)

    job = Job(
        project_id=project.id,
        status="pending",
        total_shots=num_shots,
        message="Queued for generation",
    )
    session.add(job)
    await session.commit()
    return project.id, job.id


@pytest.fixture
def mock_app() -> MagicMock:
    """Mock FastAPI app with state attributes for all clients."""
    app = MagicMock()
    app.state = SimpleNamespace(
        comfyui_client=MagicMock(),
        google_client=MagicMock(),
        openai_client=MagicMock(),
    )
    return app


@pytest.fixture
def mock_broadcast() -> Generator[AsyncMock]:
    with patch("backend.pipeline.orchestrator.manager") as m:
        m.broadcast = AsyncMock()
        yield m.broadcast


@pytest.fixture
def patch_session() -> Generator[None]:
    """Redirect orchestrator to use test DB."""
    with patch("backend.pipeline.orchestrator.async_session", db_session):
        yield


@pytest.fixture
def mock_generate_shot() -> Generator[AsyncMock]:
    with patch("backend.pipeline.orchestrator._generate_shot", new_callable=AsyncMock) as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_concatenate() -> Generator[AsyncMock]:
    with patch("backend.pipeline.orchestrator.concatenate_project", new_callable=AsyncMock) as m:
        yield m


class TestProcessJob:
    async def test_completes_all_shots(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_generate_shot: AsyncMock,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        project_id, job_id = await _create_project_with_shots(db, num_shots=2)

        await _process_job(job_id, mock_app)

        # Verify job completed
        async with db_session() as s:
            result = await s.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one()
            assert job.status == "completed"
            assert job.progress == 100
            assert job.completed_at is not None

            # Verify shots completed
            result = await s.execute(select(Shot).where(Shot.project_id == project_id))
            shots = list(result.scalars().all())
            assert all(s.status == "completed" for s in shots)

        # Verify broadcast messages
        types = [call.args[0]["type"] for call in mock_broadcast.call_args_list]
        assert types[0] == "job_progress"
        assert types.count("shot_progress") == 2
        assert types[-1] == "job_completed"

        # Verify generate_shot called for each shot
        assert mock_generate_shot.call_count == 2

    async def test_cancellation(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_generate_shot: AsyncMock,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        _, job_id = await _create_project_with_shots(db, num_shots=2)

        call_count = 0

        async def cancel_after_first(*args: object, **kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Cancel job during first shot processing
                async with db_session() as s:
                    result = await s.execute(select(Job).where(Job.id == job_id))
                    job = result.scalar_one()
                    job.status = "cancelled"
                    await s.commit()

        mock_generate_shot.side_effect = cancel_after_first

        await _process_job(job_id, mock_app)

        # Second shot should remain pending
        async with db_session() as s:
            result = await s.execute(
                select(Shot).where(Shot.project_id == (
                    select(Job.project_id).where(Job.id == job_id).scalar_subquery()
                )).order_by(Shot.order_index)
            )
            shots = list(result.scalars().all())
            assert shots[0].status == "completed"
            assert shots[1].status == "pending"

        # Should have broadcast job_failed with cancelled
        last_broadcast = mock_broadcast.call_args_list[-1].args[0]
        assert last_broadcast["error"] == "cancelled"

    async def test_error_handling(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_generate_shot: AsyncMock,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        _, job_id = await _create_project_with_shots(db, num_shots=1)

        mock_generate_shot.side_effect = RuntimeError("GPU exploded")
        await _process_job(job_id, mock_app)

        async with db_session() as s:
            result = await s.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one()
            assert job.status == "failed"
            assert "GPU exploded" in job.error

        last_broadcast = mock_broadcast.call_args_list[-1].args[0]
        assert last_broadcast["type"] == "job_failed"
        assert "GPU exploded" in last_broadcast["error"]

    async def test_missing_job(
        self, setup_db: None, mock_broadcast: AsyncMock, patch_session: None, mock_app: MagicMock
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        await _process_job("nonexistent-id", mock_app)
        mock_broadcast.assert_not_called()


class TestShotRouting:
    """Test that _generate_shot routes to the correct client based on shot.tool."""

    async def test_veo_shot_routes_to_google_client(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
        tmp_path: Path,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        project_id, job_id = await _create_project_with_shots(db, num_shots=1, tool="veo")

        fake_result = GenerationResult(
            data=b"fake-veo-video", cost_estimate=6.0, media_type="video/mp4"
        )

        with patch("backend.pipeline.orchestrator.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = str(tmp_path)
            mock_app.state.google_client.generate_video = AsyncMock(return_value=fake_result)

            await _process_job(job_id, mock_app)

            mock_app.state.google_client.generate_video.assert_called_once()

        async with db_session() as s:
            result = await s.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one()
            assert job.status == "completed"

    async def test_sora_shot_routes_to_openai_client(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
        tmp_path: Path,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        project_id, job_id = await _create_project_with_shots(db, num_shots=1, tool="sora")

        fake_result = GenerationResult(
            data=b"fake-sora-video", cost_estimate=0.40, media_type="video/mp4"
        )

        with patch("backend.pipeline.orchestrator.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = str(tmp_path)
            mock_app.state.openai_client.generate_video = AsyncMock(return_value=fake_result)

            await _process_job(job_id, mock_app)

            mock_app.state.openai_client.generate_video.assert_called_once()

    async def test_reference_image_generated_nano_banana(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
        tmp_path: Path,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        project_id, job_id = await _create_project_with_shots(
            db, num_shots=1, tool="veo", shot_type="image_to_video"
        )

        fake_image_result = GenerationResult(
            data=_make_minimal_png(), cost_estimate=0.04, media_type="image/png"
        )
        fake_video_result = GenerationResult(
            data=b"fake-video", cost_estimate=6.0, media_type="video/mp4"
        )

        with patch("backend.pipeline.orchestrator.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = str(tmp_path)
            mock_settings.return_value.default_image_tool = "nano_banana"
            mock_app.state.google_client.generate_image = AsyncMock(
                return_value=fake_image_result
            )
            mock_app.state.google_client.generate_video = AsyncMock(
                return_value=fake_video_result
            )

            await _process_job(job_id, mock_app)

            # Both image gen and video gen should be called
            mock_app.state.google_client.generate_image.assert_called_once()
            mock_app.state.google_client.generate_video.assert_called_once()

    async def test_reference_image_generated_gpt_image(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
        tmp_path: Path,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        project_id, job_id = await _create_project_with_shots(
            db, num_shots=1, tool="veo", shot_type="image_to_video"
        )

        fake_image_result = GenerationResult(
            data=_make_minimal_png(), cost_estimate=0.04, media_type="image/png"
        )
        fake_video_result = GenerationResult(
            data=b"fake-video", cost_estimate=6.0, media_type="video/mp4"
        )

        with patch("backend.pipeline.orchestrator.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = str(tmp_path)
            mock_settings.return_value.default_image_tool = "gpt_image"
            mock_app.state.openai_client.generate_image = AsyncMock(
                return_value=fake_image_result
            )
            mock_app.state.google_client.generate_video = AsyncMock(
                return_value=fake_video_result
            )

            await _process_job(job_id, mock_app)

            mock_app.state.openai_client.generate_image.assert_called_once()

    async def test_unknown_tool_raises_error(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
        tmp_path: Path,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        project_id, job_id = await _create_project_with_shots(
            db, num_shots=1, tool="invalid_tool"
        )

        with patch("backend.pipeline.orchestrator.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = str(tmp_path)

            await _process_job(job_id, mock_app)

        async with db_session() as s:
            result = await s.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one()
            assert job.status == "failed"
            assert "Unknown tool" in job.error

    async def test_mixed_tools_project(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
        tmp_path: Path,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        # Create project with 3 shots, each with a different tool
        project = Project(name="Mixed Project")
        db.add(project)
        await db.flush()

        for i, tool in enumerate(["ltx", "veo", "sora"]):
            shot = Shot(
                project_id=project.id,
                order_index=i,
                name=f"Shot {i}",
                prompt=f"Prompt {i}",
                tool=tool,
            )
            db.add(shot)

        job = Job(
            project_id=project.id,
            status="pending",
            total_shots=3,
            message="Queued",
        )
        db.add(job)
        await db.commit()

        fake_video_result = GenerationResult(
            data=b"fake-video", cost_estimate=1.0, media_type="video/mp4"
        )

        with patch("backend.pipeline.orchestrator.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = str(tmp_path)

            # LTX returns a Path
            ltx_output = tmp_path / "ltx_out.mp4"
            ltx_output.write_bytes(b"ltx-video")
            mock_app.state.comfyui_client.generate_video = AsyncMock(return_value=ltx_output)
            mock_app.state.google_client.generate_video = AsyncMock(
                return_value=fake_video_result
            )
            mock_app.state.openai_client.generate_video = AsyncMock(
                return_value=fake_video_result
            )

            await _process_job(job.id, mock_app)

            mock_app.state.comfyui_client.generate_video.assert_called_once()
            mock_app.state.google_client.generate_video.assert_called_once()
            mock_app.state.openai_client.generate_video.assert_called_once()

    async def test_cloud_error_fails_job(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
        tmp_path: Path,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        _, job_id = await _create_project_with_shots(db, num_shots=1, tool="veo")

        with patch("backend.pipeline.orchestrator.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = str(tmp_path)
            mock_app.state.google_client.generate_video = AsyncMock(
                side_effect=GoogleAPIError("Quota exceeded")
            )

            await _process_job(job_id, mock_app)

        async with db_session() as s:
            result = await s.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one()
            assert job.status == "failed"
            assert "Quota exceeded" in job.error

    async def test_veo_progress_broadcasts(
        self,
        setup_db: None,
        db: AsyncSession,
        mock_broadcast: AsyncMock,
        patch_session: None,
        mock_concatenate: AsyncMock,
        mock_app: MagicMock,
        tmp_path: Path,
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        _, job_id = await _create_project_with_shots(db, num_shots=1, tool="veo")

        fake_result = GenerationResult(
            data=b"fake-video", cost_estimate=6.0, media_type="video/mp4"
        )

        async def fake_generate_video(
            prompt: str, **kwargs: object
        ) -> GenerationResult:
            # Call the progress callback if provided
            cb = kwargs.get("progress_callback")
            if cb:
                await cb(50, 100)
                await cb(100, 100)
            return fake_result

        with patch("backend.pipeline.orchestrator.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = str(tmp_path)
            mock_app.state.google_client.generate_video = AsyncMock(
                side_effect=fake_generate_video
            )

            await _process_job(job_id, mock_app)

        # Check that shot_step_progress was broadcast
        broadcast_types = [c.args[0]["type"] for c in mock_broadcast.call_args_list]
        assert "shot_step_progress" in broadcast_types


def _make_minimal_png() -> bytes:
    """Create minimal valid PNG bytes for testing."""
    import io

    from PIL import Image

    img = Image.new("RGB", (64, 64), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
