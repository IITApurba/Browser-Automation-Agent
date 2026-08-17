import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_db_session
from apps.api.schemas.task import TaskCreate, TaskOut
from packages.db.models import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut)
async def create_task(payload: TaskCreate, session: AsyncSession = Depends(get_db_session)) -> Task:
    task = Task(name=payload.name, goal=payload.goal, extraction_schema=payload.extraction_schema)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.get("", response_model=list[TaskOut])
async def list_tasks(session: AsyncSession = Depends(get_db_session)) -> list[Task]:
    result = await session.execute(select(Task).order_by(Task.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
