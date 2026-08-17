import uuid
from datetime import datetime

from pydantic import BaseModel


class ReportOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    format: str
    file_path: str
    summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
