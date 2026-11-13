from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.api.dependencies import get_goal_service
from app.schemas.api import ApiSuccess
from app.schemas.goals import GoalCreate, GoalPatch, GoalResponse
from app.schemas.resources import GoalListParams, Page
from app.services.resources import GoalService

router = APIRouter(prefix="/goals", tags=["goals"])
Service = Annotated[GoalService, Depends(get_goal_service)]
ResourceId = Annotated[int, Path(gt=0, le=9_007_199_254_740_991)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiSuccess[GoalResponse])
async def create_resource(payload: GoalCreate, service: Service) -> ApiSuccess[GoalResponse]:
    return ApiSuccess(ok=True, data=await service.create_resource(payload))


@router.get("", response_model=ApiSuccess[Page[GoalResponse]])
async def list_resources(
    service: Service, params: Annotated[GoalListParams, Query()]
) -> ApiSuccess[Page[GoalResponse]]:
    return ApiSuccess(ok=True, data=await service.list_resources(params))


@router.patch(
    "/{resource_id}", response_model=ApiSuccess[GoalResponse], response_model_exclude_unset=True
)
async def patch_resource(
    resource_id: ResourceId, payload: GoalPatch, service: Service
) -> ApiSuccess[GoalResponse]:
    return ApiSuccess(ok=True, data=await service.patch_resource(resource_id, payload))


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(resource_id: ResourceId, service: Service) -> Response:
    await service.delete_resource(resource_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{resource_id}", response_model=ApiSuccess[GoalResponse])
async def get_resource(resource_id: ResourceId, service: Service) -> ApiSuccess[GoalResponse]:
    return ApiSuccess(
        ok=True, data=GoalResponse.model_validate(await service.require_resource(resource_id))
    )


@router.post("/{resource_id}/restore", response_model=ApiSuccess[GoalResponse])
async def restore_resource(resource_id: ResourceId, service: Service) -> ApiSuccess[GoalResponse]:
    return ApiSuccess(ok=True, data=await service.restore_resource(resource_id))
