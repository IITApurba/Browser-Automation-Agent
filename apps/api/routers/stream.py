import asyncio
import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from packages.db.models import Run, RunStatus, Step
from packages.db.session import async_session_factory

router = APIRouter(tags=["stream"])

TERMINAL_STATUSES = {RunStatus.completed, RunStatus.failed, RunStatus.paused_captcha}
POLL_INTERVAL_SECONDS = 1.0


async def _step_events(run_id: uuid.UUID):
    seen_ids: set = set()
    while True:
        async with async_session_factory() as session:
            run = await session.get(Run, run_id)
            if run is None:
                yield "event: error\ndata: run not found\n\n"
                return

            result = await session.execute(select(Step).where(Step.run_id == run_id).order_by(Step.index.asc()))
            steps = list(result.scalars().all())

        for step in steps:
            if step.id in seen_ids:
                continue
            seen_ids.add(step.id)
            payload = {
                "index": step.index,
                "type": step.type,
                "status": getattr(step.status, "value", step.status),
                "output": step.output,
            }
            yield f"event: step\ndata: {json.dumps(payload, default=str)}\n\n"

        if run.status in TERMINAL_STATUSES:
            yield f"event: done\ndata: {json.dumps({'status': getattr(run.status, 'value', run.status)})}\n\n"
            return

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: uuid.UUID) -> StreamingResponse:
    return StreamingResponse(_step_events(run_id), media_type="text/event-stream")
