from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ApiError
from app.db.session import get_db
from app.repositories.auth import AuthRepository
from app.repositories.dashboard import DashboardRepository
from app.repositories.jobs import JobRepository
from app.repositories.resources import (
    CourseRepository,
    GoalRepository,
    NoteRepository,
    PlannerRepository,
)
from app.repositories.settings import SettingsRepository
from app.repositories.timer import TimerRepository
from app.schemas.auth import SessionUser
from app.services.auth import AuthService
from app.services.dashboard import DashboardService
from app.services.jobs import JobService
from app.services.resources import CourseService, GoalService, NoteService, PlannerService
from app.services.settings import SettingsService
from app.services.timer import TimerService

DbSession = Annotated[AsyncSession, Depends(get_db, scope="function")]


def require_trusted_origin(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    allowed = get_settings().request_origins
    if origin and origin.rstrip("/") not in allowed:
        raise ApiError(403, "This request origin is not allowed.")


def get_auth_repository(session: DbSession) -> AuthRepository:
    return AuthRepository(session)


def get_auth_service(
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(repository, settings)


session_cookie = APIKeyCookie(
    name=get_settings().SESSION_COOKIE_NAME,
    auto_error=False,
    description=(
        "Log in using POST /api/v1/sessions on this same host. The browser sends the "
        "HTTPOnly session cookie automatically. No Bearer token or JWT key is used."
    ),
)


async def get_current_user(
    token: Annotated[str | None, Security(session_cookie)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionUser:
    return await service.current_user(token)


CurrentUser = Annotated[SessionUser, Depends(get_current_user)]


def get_planner_repository(session: DbSession, user: CurrentUser) -> PlannerRepository:
    return PlannerRepository(session, user.id)


def get_planner_service(
    repository: Annotated[PlannerRepository, Depends(get_planner_repository)],
) -> PlannerService:
    return PlannerService(repository)


def get_note_repository(session: DbSession, user: CurrentUser) -> NoteRepository:
    return NoteRepository(session, user.id)


def get_note_service(
    repository: Annotated[NoteRepository, Depends(get_note_repository)],
) -> NoteService:
    return NoteService(repository)


def get_goal_repository(session: DbSession, user: CurrentUser) -> GoalRepository:
    return GoalRepository(session, user.id)


def get_goal_service(
    repository: Annotated[GoalRepository, Depends(get_goal_repository)],
) -> GoalService:
    return GoalService(repository)


def get_timer_repository(session: DbSession, user: CurrentUser) -> TimerRepository:
    return TimerRepository(session, user.id)


def get_settings_repository(session: DbSession, user: CurrentUser) -> SettingsRepository:
    return SettingsRepository(session, user.id)


def get_settings_service(
    repository: Annotated[SettingsRepository, Depends(get_settings_repository)],
) -> SettingsService:
    return SettingsService(repository)


def get_timer_service(
    repository: Annotated[TimerRepository, Depends(get_timer_repository)],
    preferences: Annotated[SettingsService, Depends(get_settings_service)],
) -> TimerService:
    return TimerService(repository, preferences)


def get_dashboard_repository(session: DbSession, user: CurrentUser) -> DashboardRepository:
    return DashboardRepository(session, user.id)


def get_dashboard_service(
    repository: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
) -> DashboardService:
    return DashboardService(repository)


def get_job_repository(session: DbSession, user: CurrentUser) -> JobRepository:
    return JobRepository(session, user.id)


def get_job_service(
    repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> JobService:
    return JobService(repository)


def get_course_repository(session: DbSession, user: CurrentUser) -> CourseRepository:
    return CourseRepository(session, user.id)


def get_course_service(
    repository: Annotated[CourseRepository, Depends(get_course_repository)],
) -> CourseService:
    return CourseService(repository)
