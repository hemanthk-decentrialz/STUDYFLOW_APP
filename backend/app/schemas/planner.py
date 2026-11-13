from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.schemas.resources import RequestModel, ResourcePatch, SafeId, Title, parse_calendar_date

Priority = Literal["High", "Medium", "Low"]
StudyTime = Annotated[str, StringConstraints(strict=True, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]
Duration = Annotated[int, Field(strict=True, ge=15, le=2_147_483_647)]


class StudySessionCreate(RequestModel):
    goal_id: SafeId | None = Field(default=None, alias="goalId")
    course_id: SafeId = Field(
        alias="courseId", description="An active course owned by this session user."
    )
    id: SafeId = Field(description="Positive JavaScript-safe numeric ID; immutable after creation.")
    subject: Title | None = Field(
        default=None, description="Compatibility label; derived from courseId by the service."
    )
    scheduled_date: date | None = Field(
        default=None,
        alias="scheduledDate",
        description="Local calendar date in YYYY-MM-DD. Older undated sessions stay unscheduled.",
    )
    time: StudyTime = Field(description="Local study start time in 24-hour HH:MM format.")
    duration_minutes: Duration = Field(default=60, alias="durationMinutes")
    priority: Priority = "Medium"
    completed: bool = Field(default=False, strict=True)
    _date = field_validator("scheduled_date", mode="before")(parse_calendar_date)


class StudySessionPatch(ResourcePatch):
    nullable_fields = frozenset({"goal_id"})
    course_id: SafeId | None = Field(default=None, alias="courseId")
    goal_id: SafeId | None = Field(default=None, alias="goalId")
    scheduled_date: date | None = Field(default=None, alias="scheduledDate")
    _date = field_validator("scheduled_date", mode="before")(parse_calendar_date)
    time: StudyTime | None = None
    duration_minutes: Duration | None = Field(default=None, alias="durationMinutes")
    priority: Priority | None = None
    completed: bool | None = Field(default=None, strict=True)


class StudySessionResponse(BaseModel):
    goal_id: int | None = Field(default=None, serialization_alias="goalId")
    course_id: int = Field(serialization_alias="courseId")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int
    subject: str
    time: str
    scheduled_date: date | None = Field(default=None, serialization_alias="scheduledDate")
    duration_minutes: int = Field(serialization_alias="durationMinutes")
    priority: Priority
    completed: bool
