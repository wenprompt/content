from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Job, Project, Shot
from tests.conftest import db_session


async def _create_project_with_shots(session: AsyncSession, num_shots: int = 2) -> tuple[str, str]:
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
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        project_id, job_id = await _create_project_with_shots(db, num_shots=2)

        await _process_job(job_id)

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

        await _process_job(job_id)

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
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        _, job_id = await _create_project_with_shots(db, num_shots=1)

        mock_generate_shot.side_effect = RuntimeError("GPU exploded")
        await _process_job(job_id)

        async with db_session() as s:
            result = await s.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one()
            assert job.status == "failed"
            assert "GPU exploded" in job.error

        last_broadcast = mock_broadcast.call_args_list[-1].args[0]
        assert last_broadcast["type"] == "job_failed"
        assert "GPU exploded" in last_broadcast["error"]

    async def test_missing_job(
        self, setup_db: None, mock_broadcast: AsyncMock, patch_session: None
    ) -> None:
        from backend.pipeline.orchestrator import _process_job

        await _process_job("nonexistent-id")
        mock_broadcast.assert_not_called()
