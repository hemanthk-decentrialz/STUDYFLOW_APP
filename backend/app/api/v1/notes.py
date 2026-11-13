from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.api.dependencies import get_note_service
from app.schemas.api import ApiSuccess
from app.schemas.notes import NoteCreate, NotePatch, NoteResponse
from app.schemas.resources import NoteListParams, Page
from app.services.resources import NoteService

router = APIRouter(prefix="/notes", tags=["notes"])
Service = Annotated[NoteService, Depends(get_note_service)]
ResourceId = Annotated[int, Path(gt=0, le=9_007_199_254_740_991)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiSuccess[NoteResponse])
async def create_resource(payload: NoteCreate, service: Service) -> ApiSuccess[NoteResponse]:
    return ApiSuccess(ok=True, data=await service.create_resource(payload))


@router.get("", response_model=ApiSuccess[Page[NoteResponse]])
async def list_resources(
    service: Service, params: Annotated[NoteListParams, Query()]
) -> ApiSuccess[Page[NoteResponse]]:
    return ApiSuccess(ok=True, data=await service.list_resources(params))


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(resource_id: ResourceId, service: Service) -> Response:
    await service.delete_resource(resource_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{resource_id}", response_model=ApiSuccess[NoteResponse])
async def get_note(resource_id: ResourceId, service: Service) -> ApiSuccess[NoteResponse]:
    return ApiSuccess(
        ok=True, data=NoteResponse.model_validate(await service.require_resource(resource_id))
    )


@router.patch("/{resource_id}", response_model=ApiSuccess[NoteResponse])
async def patch_note(
    resource_id: ResourceId, payload: NotePatch, service: Service
) -> ApiSuccess[NoteResponse]:
    return ApiSuccess(ok=True, data=await service.patch_resource(resource_id, payload))


@router.post("/{resource_id}/restore", response_model=ApiSuccess[NoteResponse])
async def restore_resource(resource_id: ResourceId, service: Service) -> ApiSuccess[NoteResponse]:
    return ApiSuccess(ok=True, data=await service.restore_resource(resource_id))
