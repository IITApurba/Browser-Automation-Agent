import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_db_session
from apps.api.schemas.run import RunOut, StepOut
from apps.api.settings import settings
from packages.agent.llm import get_chat_model
from packages.agent.runner import GraphRunner
from packages.db.models import Run, RunStatus, Step, Task
from packages.db.session import async_session_factory
from packages.reporting.generator import ReportGenerator

router = APIRouter(tags=["runs"])


@router.post("/tasks/{task_id}/runs", response_model=RunOut)
async def create_run(
    task_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> Run:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    run = Run(task_id=task.id, status=RunStatus.pending)
    session.add(run)
    await session.commit()
    await session.refresh(run)

    llm = get_chat_model(settings.llm_provider)
    runner = GraphRunner()
    background_tasks.add_task(
        runner.run,
        str(task.id),
        str(run.id),
        task.goal,
        task.extraction_schema,
        async_session_factory,
        llm,
        None,
    )
    return run


@router.get("/runs", response_model=list[RunOut])
async def list_runs(session: AsyncSession = Depends(get_db_session)) -> list[Run]:
    result = await session.execute(select(Run).order_by(Run.created_at.desc()))
    return list(result.scalars().all())


@router.get("/runs/{run_id}", response_model=RunOut)
async def get_run(run_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)) -> Run:
    run = await session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/steps", response_model=list[StepOut])
async def get_steps(run_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)) -> list[Step]:
    result = await session.execute(select(Step).where(Step.run_id == run_id).order_by(Step.index.asc()))
    return list(result.scalars().all())


@router.get("/runs/{run_id}/report")
async def get_report(run_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    run = await session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    result = await session.execute(select(Step).where(Step.run_id == run_id).order_by(Step.index.asc()))
    steps = list(result.scalars().all())

    extracted_data: list = []
    for step in steps:
        output = step.output or {}
        result_data = (output.get("last_action_result") or {}).get("data")
        if result_data:
            extracted_data.append(result_data)

    generator = ReportGenerator()
    markdown = generator.generate(run, steps, extracted_data)
    return {"run_id": str(run_id), "markdown": markdown}


@router.get("/runs/{run_id}/report/download")
async def download_report(run_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)) -> FileResponse:
    run = await session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    result = await session.execute(select(Step).where(Step.run_id == run_id).order_by(Step.index.asc()))
    steps = list(result.scalars().all())

    extracted_data: list = []
    for step in steps:
        output = step.output or {}
        result_data = (output.get("last_action_result") or {}).get("data")
        if result_data:
            extracted_data.append(result_data)

    generator = ReportGenerator()
    markdown = generator.generate(run, steps, extracted_data)
    path = generator.save(run_id, markdown)
    if not os.path.exists(path):
        raise HTTPException(status_code=500, detail="Failed to write report")
    return FileResponse(path, filename=f"{run_id}.md", media_type="text/markdown")
