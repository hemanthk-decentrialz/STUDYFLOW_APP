from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_timer_service
from app.schemas.api import ApiSuccess
from app.schemas.timer import TimerPatchRequest, TimerState
from app.services.timer import TimerService

router = APIRouter(prefix="/timers", tags=["pomodoro timer"])
TimerServiceDependency = Annotated[TimerService, Depends(get_timer_service)]


@router.get("/current", response_model=ApiSuccess[TimerState])
async def get_timer(service: TimerServiceDependency) -> ApiSuccess[TimerState]:
    return ApiSuccess(ok=True, data=await service.get_timer())


@router.patch(
    "/current",
    response_model=ApiSuccess[TimerState],
    response_model_exclude_unset=True,
)
async def save_timer(
    payload: TimerPatchRequest, service: TimerServiceDependency
) -> ApiSuccess[TimerState]:
    return ApiSuccess(ok=True, data=await service.patch_timer(payload))
