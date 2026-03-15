import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.jobs import router as jobs_router
from backend.api.projects import router as projects_router
from backend.api.trends import router as trends_router
from backend.api.websocket import router as ws_router
from backend.clients.comfyui_client import ComfyUIClient
from backend.clients.google_client import GoogleClient
from backend.clients.openai_client import OpenAIClient
from backend.config import get_settings
from backend.database import init_db
from backend.pipeline.orchestrator import process_job_queue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Startup
    await init_db()
    app.state.http_client = httpx.AsyncClient(timeout=60.0)
    app.state.job_queue = asyncio.Queue[str]()

    settings = get_settings()
    app.state.comfyui_client = ComfyUIClient(settings.comfyui_url)
    app.state.google_client = (
        GoogleClient(api_key=settings.gemini_api_key) if settings.gemini_api_key else None
    )
    app.state.openai_client = (
        OpenAIClient(api_key=settings.openai_api_key) if settings.openai_api_key else None
    )

    worker_task = asyncio.create_task(process_job_queue(app))
    yield

    # Shutdown
    worker_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await worker_task
    await app.state.http_client.aclose()


app = FastAPI(
    title="Content Pipeline API",
    description="AI Content Creation Pipeline — Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(projects_router)
app.include_router(jobs_router)
app.include_router(trends_router)
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
