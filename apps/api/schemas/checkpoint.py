import uuid
from datetime import datetime

from pydantic import BaseModel


class CheckpointOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    step_id: uuid.UUID | None = None
    reason: str
    page_url: str
    extracted_so_far: dict | list | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckpointResumeRequest(BaseModel):
    resolved_by: str | None = None
