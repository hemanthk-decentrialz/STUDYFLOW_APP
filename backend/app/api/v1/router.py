from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import require_trusted_origin
from app.api.v1.auth import router as auth_router
from app.api.v1.courses import router as courses_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.focus_sessions import router as focus_router
from app.api.v1.goals import router as goals_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.notes import router as notes_router
from app.api.v1.planner import router as planner_router
from app.api.v1.settings import router as settings_router
from app.api.v1.timer import router as timer_router
from app.schemas.api import ApiFailure

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": ApiFailure, "description": description}
    for code, description in {
        400: "Malformed request",
        401: "Cookie session required",
        403: "Untrusted origin",
        404: "Owned resource not found",
        409: "Conflict or reset in progress",
        413: "Request body too large",
        422: "Validation failed",
        429: "Rate limit exceeded",
        500: "Unexpected error; details recorded only in server logs",
        503: "Dependency unavailable",
    }.items()
}
api_router = APIRouter(
    prefix="/api/v1", dependencies=[Depends(require_trusted_origin)], responses=ERROR_RESPONSES
)
api_router.include_router(auth_router)
api_router.include_router(courses_router)
api_router.include_router(planner_router)
api_router.include_router(notes_router)
api_router.include_router(goals_router)
api_router.include_router(timer_router)
api_router.include_router(focus_router)
api_router.include_router(settings_router)
api_router.include_router(dashboard_router)
api_router.include_router(jobs_router)
api_router.include_router(health_router)
