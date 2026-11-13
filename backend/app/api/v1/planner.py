from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.api.dependencies import get_planner_service
from app.schemas.api import ApiSuccess
from app.schemas.planner import StudySessionCreate, StudySessionPatch, StudySessionResponse
from app.schemas.resources import Page, PlannerListParams
from app.services.resources import PlannerService

router = APIRouter(prefix="/study-sessions", tags=["planner"])
Service = Annotated[PlannerService, Depends(get_planner_service)]
ResourceId = Annotated[int, Path(gt=0, le=9_007_199_254_740_991)]


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=ApiSuccess[StudySessionResponse]
)
async def create_resource(
    payload: StudySessionCreate, service: Service
) -> ApiSuccess[StudySessionResponse]:
    return ApiSuccess(ok=True, data=await service.create_resource(payload))


@router.get("", response_model=ApiSuccess[Page[StudySessionResponse]])
async def list_resources(
    service: Service, params: Annotated[PlannerListParams, Query()]
) -> ApiSuccess[Page[StudySessionResponse]]:
    return ApiSuccess(ok=True, data=await service.list_resources(params))


@router.patch(
    "/{resource_id}",
    response_model=ApiSuccess[StudySessionResponse],
    response_model_exclude_unset=True,
)
async def patch_resource(
    resource_id: ResourceId, payload: StudySessionPatch, service: Service
) -> ApiSuccess[StudySessionResponse]:
    return ApiSuccess(ok=True, data=await service.patch_resource(resource_id, payload))


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(resource_id: ResourceId, service: Service) -> Response:
    await service.delete_resource(resource_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{resource_id}/restore", response_model=ApiSuccess[StudySessionResponse])
async def restore_resource(
    resource_id: ResourceId, service: Service
) -> ApiSuccess[StudySessionResponse]:
    return ApiSuccess(ok=True, data=await service.restore_resource(resource_id))
