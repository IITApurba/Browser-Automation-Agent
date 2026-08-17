import uuid
from datetime import datetime

from pydantic import BaseModel


class TaskCreate(BaseModel):
    name: str
    goal: str
    extraction_schema: dict | None = None


class TaskOut(BaseModel):
    id: uuid.UUID
    name: str
    goal: str
    extraction_schema: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
