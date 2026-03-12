from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import get_db
from backend.main import app
from backend.models import Base

# In-memory SQLite for tests — isolated from dev DB
test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
db_session = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db() -> AsyncGenerator[None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    async with db_session() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    async def _override_db() -> AsyncGenerator[AsyncSession]:
        async with db_session() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    # Set up app.state for job queue
    import asyncio

    app.state.job_queue = asyncio.Queue()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
