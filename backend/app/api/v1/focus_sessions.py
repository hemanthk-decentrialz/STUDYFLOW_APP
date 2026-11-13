from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_timer_service
from app.schemas.api import ApiSuccess
from app.schemas.dashboard import DashboardQuery
from app.schemas.resources import Page
from app.schemas.timer import FocusListParams, FocusResponse, FocusSummary
from app.services.timer import TimerService

router = APIRouter(prefix="/focus-sessions", tags=["focus history"])
Service = Annotated[TimerService, Depends(get_timer_service)]


@router.get("", response_model=ApiSuccess[Page[FocusResponse]])
async def list_focus(
    service: Service, params: Annotated[FocusListParams, Query()]
) -> ApiSuccess[Page[FocusResponse]]:
    return ApiSuccess(ok=True, data=await service.focus_page(params))


@router.get("/summary", response_model=ApiSuccess[FocusSummary])
async def focus_summary(
    service: Service, query: Annotated[DashboardQuery, Query()]
) -> ApiSuccess[FocusSummary]:
    return ApiSuccess(ok=True, data=await service.focus_summary(query.time_zone))
