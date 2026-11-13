from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_dashboard_service
from app.schemas.api import ApiSuccess
from app.schemas.dashboard import DashboardQuery, DashboardSummary
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboards", tags=["dashboard"])


@router.get("/summary", response_model=ApiSuccess[DashboardSummary])
async def get_dashboard(
    query: Annotated[DashboardQuery, Query()],
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> ApiSuccess[DashboardSummary]:
    return ApiSuccess(ok=True, data=await service.summary(query.time_zone))
