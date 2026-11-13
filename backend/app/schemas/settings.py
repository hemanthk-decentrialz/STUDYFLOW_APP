from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.dashboard import DashboardQuery
from app.schemas.resources import ResourceListParams, ResourcePatch

FocusMinutes = Annotated[int, Field(strict=True, ge=1, le=120)]
ShortMinutes = Annotated[int, Field(strict=True, ge=1, le=30)]
LongMinutes = Annotated[int, Field(strict=True, ge=1, le=60)]
LeadMinutes = Annotated[int, Field(strict=True, ge=5, le=120)]


class SettingsState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theme: Literal["light", "dark"] = "light"
    focusMinutes: FocusMinutes = 25
    shortBreakMinutes: ShortMinutes = 5
    longBreakMinutes: LongMinutes = 15
    completionSound: bool = Field(default=True, strict=True)
    weekStartsOn: Literal["monday", "sunday"] = "monday"
    timeZone: str = Field(default="UTC", min_length=1, max_length=100)
    timeFormat: Literal["12h", "24h"] = "24h"
    sessionReminders: bool = Field(default=False, strict=True)
    deadlineReminders: bool = Field(default=False, strict=True)
    reminderLeadMinutes: LeadMinutes = 15

    @field_validator("timeZone")
    @classmethod
    def valid_zone(cls, value: str) -> str:
        return DashboardQuery.valid_zone(value)

    @property
    def durations(self) -> dict[str, int]:
        return {
            "Pomodoro": self.focusMinutes * 60,
            "Short Break": self.shortBreakMinutes * 60,
            "Long Break": self.longBreakMinutes * 60,
        }


class SettingsChanges(ResourcePatch):
    theme: Literal["light", "dark"] | None = None
    focusMinutes: FocusMinutes | None = None
    shortBreakMinutes: ShortMinutes | None = None
    longBreakMinutes: LongMinutes | None = None
    completionSound: Annotated[bool, Field(strict=True)] | None = None
    weekStartsOn: Literal["monday", "sunday"] | None = None
    timeZone: str | None = Field(default=None, min_length=1, max_length=100)
    timeFormat: Literal["12h", "24h"] | None = None
    sessionReminders: Annotated[bool, Field(strict=True)] | None = None
    deadlineReminders: Annotated[bool, Field(strict=True)] | None = None
    reminderLeadMinutes: LeadMinutes | None = None

    @field_validator("timeZone")
    @classmethod
    def valid_zone(cls, value: str | None) -> str | None:
        return DashboardQuery.valid_zone(value) if value is not None else None


class SettingsPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    settings: SettingsChanges


class TrashParams(ResourceListParams):
    sort_by: Literal["deleted_at"] = "deleted_at"
    order: Literal["asc", "desc"] = "desc"
    kind: Literal["courses", "notes", "goals", "study-sessions"] | None = None


class DeletedResource(BaseModel):
    id: int
    kind: Literal["courses", "notes", "goals", "study-sessions"]
    title: str
    deletedAt: datetime
    courseId: int | None


class ReminderResponse(BaseModel):
    id: str
    title: str
    dueAt: datetime
    kind: Literal["study-sessions", "goals"]
