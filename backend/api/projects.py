import json
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models import Project, Shot
from backend.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ShotCreate,
    ShotReorder,
    ShotResponse,
    ShotUpdate,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])

DB = Annotated[AsyncSession, Depends(get_db)]


# --- Project CRUD ---


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: DB) -> Project:
    project = Project(**data.model_dump())
    db.add(project)
    await db.commit()
    # Re-fetch with eager load to avoid lazy-load in async context
    result = await db.execute(
        select(Project).where(Project.id == project.id).options(selectinload(Project.shots))
    )
    return result.scalar_one()


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: DB) -> list[Project]:
    result = await db.execute(
        select(Project).options(selectinload(Project.shots)).order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: DB) -> Project:
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.shots))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, db: DB) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    result = await db.execute(
        select(Project).where(Project.id == project_id).options(selectinload(Project.shots))
    )
    return result.scalar_one()


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: DB) -> None:
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.shots), selectinload(Project.jobs))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()


# --- Shot CRUD (nested under project) ---


async def _get_project(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/shots", response_model=ShotResponse, status_code=201)
async def create_shot(project_id: str, data: ShotCreate, db: DB) -> Shot:
    await _get_project(project_id, db)
    # Auto-set order_index to next available
    result = await db.execute(
        select(Shot)
        .where(Shot.project_id == project_id)
        .order_by(Shot.order_index.desc())
        .limit(1)
    )
    last_shot = result.scalar_one_or_none()
    next_index = (last_shot.order_index + 1) if last_shot else 0

    shot = Shot(**data.model_dump(), project_id=project_id, order_index=next_index)
    db.add(shot)
    await db.commit()
    await db.refresh(shot)
    return shot


# Reorder must be defined BEFORE {shot_id} routes to avoid path conflict
@router.put("/{project_id}/shots/reorder", response_model=list[ShotResponse])
async def reorder_shots(project_id: str, data: ShotReorder, db: DB) -> list[Shot]:
    await _get_project(project_id, db)
    result = await db.execute(
        select(Shot).where(Shot.project_id == project_id)
    )
    shots_by_id = {s.id: s for s in result.scalars().all()}

    for idx, shot_id in enumerate(data.shot_ids):
        if shot_id not in shots_by_id:
            raise HTTPException(status_code=404, detail=f"Shot {shot_id} not found")
        shots_by_id[shot_id].order_index = idx

    await db.commit()
    return [shots_by_id[sid] for sid in data.shot_ids]


@router.put("/{project_id}/shots/{shot_id}", response_model=ShotResponse)
async def update_shot(project_id: str, shot_id: str, data: ShotUpdate, db: DB) -> Shot:
    result = await db.execute(
        select(Shot).where(Shot.id == shot_id, Shot.project_id == project_id)
    )
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(shot, key, value)
    await db.commit()
    await db.refresh(shot)
    return shot


@router.delete("/{project_id}/shots/{shot_id}", status_code=204)
async def delete_shot(project_id: str, shot_id: str, db: DB) -> None:
    result = await db.execute(
        select(Shot).where(Shot.id == shot_id, Shot.project_id == project_id)
    )
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    await db.delete(shot)
    await db.commit()


# --- Upload ---


@router.post("/{project_id}/upload", response_model=ProjectResponse)
async def upload_reference(project_id: str, file: UploadFile, db: DB) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    upload_dir = Path("output") / project_id / "references"
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename).name
    file_path = upload_dir / safe_name
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    images: list[str] = json.loads(project.reference_images)
    images.append(str(file_path))
    project.reference_images = json.dumps(images)

    await db.commit()
    result = await db.execute(
        select(Project).where(Project.id == project_id).options(selectinload(Project.shots))
    )
    return result.scalar_one()
