import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_db_session
from apps.api.schemas.checkpoint import CheckpointOut, CheckpointResumeRequest
from apps.api.settings import settings
from packages.agent.llm import get_chat_model
from packages.agent.runner import GraphRunner
from packages.db.models import Checkpoint
from packages.db.session import async_session_factory

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


@router.get("", response_model=list[CheckpointOut])
async def list_checkpoints(resolved: bool | None = None, session: AsyncSession = Depends(get_db_session)) -> list[Checkpoint]:
    stmt = select(Checkpoint).order_by(Checkpoint.created_at.desc())
    if resolved is not None:
        if resolved:
            stmt = stmt.where(Checkpoint.resolved_at.is_not(None))
        else:
            stmt = stmt.where(Checkpoint.resolved_at.is_(None))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/{checkpoint_id}/resume", response_model=CheckpointOut)
async def resume_checkpoint(
    checkpoint_id: uuid.UUID,
    payload: CheckpointResumeRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> Checkpoint:
    checkpoint = await session.get(Checkpoint, checkpoint_id)
    if checkpoint is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    checkpoint.resolved_at = datetime.now(timezone.utc)
    checkpoint.resolved_by = payload.resolved_by or "dashboard"
    await session.commit()
    await session.refresh(checkpoint)

    llm = get_chat_model(settings.llm_provider)
    runner = GraphRunner()
    background_tasks.add_task(
        runner.resume_from_checkpoint,
        str(checkpoint.id),
        async_session_factory,
        llm,
        None,
    )
    return checkpoint
