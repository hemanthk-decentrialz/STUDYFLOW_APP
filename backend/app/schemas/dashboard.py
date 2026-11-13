from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from app.schemas.goals import GoalResponse
from app.schemas.planner import StudySessionResponse
from app.schemas.resources import RequestModel


class DashboardQuery(RequestModel):
    time_zone: str = Field(default="UTC", max_length=100)

    @field_validator("time_zone")
    @classmethod
    def valid_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Use a valid IANA time zone.") from exc
        return value


class DashboardSummary(BaseModel):
    plannerCount: int
    completedGoals: int
    pendingGoals: int
    totalGoals: int
    completionRate: int
    completedPlanner: int
    pendingPlanner: int
    plannerCompletionRate: int
    totalNotes: int
    totalSessions: int
    activeGoalTitle: str
    date: date
    timeZone: str
    todaySessions: list[StudySessionResponse]
    nextSession: StudySessionResponse | None
    upcomingGoals: list[GoalResponse]
    todaySessionCount: int
    todayCompletedCount: int
    todayPlannedMinutes: int
    undatedPlannerCount: int
    overdueGoalCount: int
