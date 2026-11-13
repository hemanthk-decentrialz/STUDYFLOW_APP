from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.api.dependencies import get_course_service
from app.schemas.api import ApiSuccess
from app.schemas.courses import CourseCreate, CourseListParams, CoursePatch, CourseResponse
from app.schemas.resources import Page
from app.services.resources import CourseService

router = APIRouter(prefix="/courses", tags=["courses"])
Service = Annotated[CourseService, Depends(get_course_service)]
ResourceId = Annotated[int, Path(gt=0, le=9_007_199_254_740_991)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiSuccess[CourseResponse])
async def create_resource(payload: CourseCreate, service: Service) -> ApiSuccess[CourseResponse]:
    return ApiSuccess(ok=True, data=await service.create_resource(payload))


@router.get("", response_model=ApiSuccess[Page[CourseResponse]])
async def list_resources(
    service: Service, params: Annotated[CourseListParams, Query()]
) -> ApiSuccess[Page[CourseResponse]]:
    return ApiSuccess(ok=True, data=await service.list_resources(params))


@router.patch(
    "/{resource_id}",
    response_model=ApiSuccess[CourseResponse],
    response_model_exclude_unset=True,
)
async def patch_resource(
    resource_id: ResourceId, payload: CoursePatch, service: Service
) -> ApiSuccess[CourseResponse]:
    return ApiSuccess(ok=True, data=await service.patch_resource(resource_id, payload))


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(resource_id: ResourceId, service: Service) -> Response:
    await service.delete_resource(resource_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{resource_id}", response_model=ApiSuccess[CourseResponse])
async def get_resource(resource_id: ResourceId, service: Service) -> ApiSuccess[CourseResponse]:
    return ApiSuccess(
        ok=True, data=CourseResponse.model_validate(await service.require_resource(resource_id))
    )


@router.post("/{resource_id}/restore", response_model=ApiSuccess[CourseResponse])
async def restore_resource(resource_id: ResourceId, service: Service) -> ApiSuccess[CourseResponse]:
    return ApiSuccess(ok=True, data=await service.restore_resource(resource_id))
