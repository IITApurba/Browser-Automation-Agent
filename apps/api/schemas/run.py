import uuid
from datetime import datetime

from pydantic import BaseModel


class RunCreate(BaseModel):
    pass


class RunOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    status: str
    plan: dict | None = None
    current_step_index: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StepOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    index: int
    type: str
    input: dict | None = None
    output: dict | None = None
    status: str
    dom_fingerprint: str | None = None
    screenshot_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
