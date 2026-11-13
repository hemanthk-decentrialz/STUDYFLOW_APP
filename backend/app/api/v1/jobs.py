from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status

from app.api.dependencies import get_job_service
from app.schemas.api import ApiSuccess
from app.schemas.jobs import JobResponse
from app.services.jobs import JobService
from app.tasks.resets import NativeTaskDispatcher

router = APIRouter(prefix="/data-resets", tags=["data resets"])
Service = Annotated[JobService, Depends(get_job_service)]
Dispatcher = Annotated[NativeTaskDispatcher, Depends(NativeTaskDispatcher)]


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiSuccess[JobResponse],
    summary="Queue an atomic hard reset of the current user's study data",
)
async def enqueue_reset(
    service: Service, tasks: BackgroundTasks, response: Response, dispatcher: Dispatcher
) -> ApiSuccess[JobResponse]:
    job = await service.enqueue_reset()
    dispatcher.enqueue_reset(tasks, job.id)
    response.headers["Location"] = "/api/v1/data-resets/current"
    return ApiSuccess(ok=True, data=job)


@router.get(
    "/current",
    response_model=ApiSuccess[JobResponse | None],
    summary="Read the latest owned reset job for polling or recovery",
)
async def current_reset(service: Service) -> ApiSuccess[JobResponse | None]:
    return ApiSuccess(ok=True, data=await service.current())
