from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID = Field(description="Owner-scoped job identifier used for polling.")
    kind: Literal["study-data-reset"]
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    completed_at: datetime | None
    error: str | None = Field(description="Safe failure message, never a stack trace.")
