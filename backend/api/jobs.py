from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models import Job, Project
from backend.schemas import JobResponse

router = APIRouter(tags=["jobs"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/api/projects/{project_id}/generate", response_model=JobResponse, status_code=201
)
async def generate(project_id: str, request: Request, db: DB) -> Job:
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.shots))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = Job(
        project_id=project_id,
        status="pending",
        total_shots=len(project.shots),
        message="Queued for generation",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await request.app.state.job_queue.put(job.id)
    return job


@router.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: DB) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/api/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(job_id: str, db: DB) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "cancelled"
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/api/projects/{project_id}/jobs", response_model=list[JobResponse])
async def list_jobs(project_id: str, db: DB) -> list[Job]:
    result = await db.execute(
        select(Job).where(Job.project_id == project_id).order_by(Job.created_at.desc())
    )
    return list(result.scalars().all())
