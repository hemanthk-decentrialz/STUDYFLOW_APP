from datetime import date, datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.resources import RequestModel, ResourceListParams, SafeId

TimerMode = Literal["Pomodoro", "Short Break", "Long Break"]


class TimerState(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="forbid")

    course_id: int | None = Field(default=None, alias="courseId")
    active_focus_id: UUID | None = Field(default=None, alias="activeFocusId")
    block_duration: int = Field(default=1500, ge=60, le=7200, alias="blockDuration")
    revision: int = 0
    mode: TimerMode = "Pomodoro"
    time_left: int = Field(default=1500, ge=0, le=2_147_483_647, alias="timeLeft")
    is_running: bool = Field(default=False, alias="isRunning")
    completed_sessions: int = Field(default=0, ge=0, le=2_147_483_647, alias="completedSessions")
    end_at: int | None = Field(
        default=None,
        ge=0,
        le=9_007_199_254_740_991,
        alias="endAt",
        exclude_if=lambda value: value is None,
    )
    last_completed_at: int | None = Field(
        default=None,
        ge=0,
        le=9_007_199_254_740_991,
        alias="lastCompletedAt",
        exclude_if=lambda value: value is None,
    )
    last_completed_mode: TimerMode | None = Field(
        default=None, alias="lastCompletedMode", exclude_if=lambda value: value is None
    )


class TimerPatch(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    course_id: SafeId | None = Field(default=None, alias="courseId")
    mode: TimerMode | None = None
    time_left: int | None = Field(
        default=None, strict=True, ge=0, le=2_147_483_647, alias="timeLeft"
    )
    is_running: bool | None = Field(default=None, strict=True, alias="isRunning")

    @model_validator(mode="after")
    def require_valid_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one timer field.")
        for field in self.model_fields_set - {"course_id"}:
            if getattr(self, field) is None:
                raise ValueError("Required timer fields cannot be null.")
        return self


class TimerPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(alias="expectedRevision", strict=True, ge=0)
    timer: TimerPatch


class FocusListParams(RequestModel):
    page: int = Field(default=1, ge=1, le=10001)
    limit: int = Field(default=10, ge=1, le=100)

    @model_validator(mode="after")
    def bounded(self) -> Self:
        ResourceListParams.bounded_offset(self)
        return self

    sort_by: Literal["started_at"] = "started_at"
    order: Literal["asc", "desc"] = "desc"
    course_id: int | None = Field(default=None, gt=0, le=9_007_199_254_740_991)


class FocusResponse(BaseModel):
    id: UUID
    courseId: int | None
    courseTitle: str
    startedAt: datetime
    endedAt: datetime | None
    seconds: int
    outcome: Literal["running", "paused", "completed", "cancelled"]


class FocusDay(BaseModel):
    date: date
    seconds: int


class FocusCourse(BaseModel):
    courseId: int | None
    title: str
    seconds: int


class FocusSummary(BaseModel):
    weekStart: date
    timeZone: str
    seconds: int
    completedPomodoros: int
    days: list[FocusDay]
    courses: list[FocusCourse]
