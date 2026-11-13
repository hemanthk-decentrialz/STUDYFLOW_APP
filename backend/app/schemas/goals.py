from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.resources import RequestModel, ResourcePatch, SafeId, Title, parse_calendar_date

Progress = Annotated[int, Field(strict=True, ge=0, le=100)]


class GoalCreate(RequestModel):
    course_id: SafeId = Field(
        alias="courseId", description="An active course owned by this session user."
    )
    id: SafeId = Field(description="Positive JavaScript-safe numeric ID; immutable after creation.")
    title: Title = Field(description="Trimmed title, unique per owner among active resources.")
    subject: Title | None = Field(
        default=None, description="Compatibility label; derived from courseId by the service."
    )
    deadline: date = Field(
        description="Calendar deadline in YYYY-MM-DD format; overdue dates remain valid."
    )
    progress: Progress = 0
    _deadline = field_validator("deadline", mode="before")(parse_calendar_date)


class GoalPatch(ResourcePatch):
    title: Title | None = None
    deadline: date | None = None
    progress: Progress | None = None
    _deadline = field_validator("deadline", mode="before")(parse_calendar_date)


class GoalResponse(BaseModel):
    linked_session_count: int = Field(default=0, serialization_alias="linkedSessionCount")
    completed_session_count: int = Field(default=0, serialization_alias="completedSessionCount")
    course_id: int = Field(serialization_alias="courseId")
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    subject: str
    deadline: date = Field(
        description="Calendar deadline in YYYY-MM-DD format; overdue dates remain valid."
    )
    progress: int
