import asyncio
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_settings_service
from app.schemas.api import ApiSuccess
from app.schemas.resources import Page
from app.schemas.settings import (
    DeletedResource,
    ReminderResponse,
    SettingsPatchRequest,
    SettingsState,
    TrashParams,
)
from app.services.settings import SettingsService

router = APIRouter(tags=["settings"])
SettingsServiceDependency = Annotated[SettingsService, Depends(get_settings_service)]


@router.get("/preferences", response_model=ApiSuccess[SettingsState])
async def get_settings(service: SettingsServiceDependency) -> ApiSuccess[SettingsState]:
    return ApiSuccess(ok=True, data=await service.get_settings())


@router.patch(
    "/preferences", response_model=ApiSuccess[SettingsState], response_model_exclude_unset=True
)
async def save_settings(
    payload: SettingsPatchRequest, service: SettingsServiceDependency
) -> ApiSuccess[SettingsState]:
    return ApiSuccess(ok=True, data=await service.patch_settings(payload))


@router.get(
    "/deleted-resources",
    response_model=ApiSuccess[Page[DeletedResource]],
    summary="Review my recently deleted study resources",
)
async def deleted_resources(
    params: Annotated[TrashParams, Query()], service: SettingsServiceDependency
) -> ApiSuccess[Page[DeletedResource]]:
    return ApiSuccess(ok=True, data=await service.deleted_page(params))


@router.get(
    "/reminders",
    response_model=ApiSuccess[list[ReminderResponse]],
    summary="Due reminders using my saved calendar preferences",
)
async def reminders(service: SettingsServiceDependency) -> ApiSuccess[list[ReminderResponse]]:
    return ApiSuccess(ok=True, data=await service.reminders())


@router.get(
    "/data-exports",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"application/json": {}},
            "description": (
                "Versioned JSON download of my study data, including deleted resources; "
                "excludes credentials and sessions"
            ),
        }
    },
)
async def export_data(service: SettingsServiceDependency) -> StreamingResponse:
    output = await service.export_data()

    async def chunks() -> AsyncIterator[bytes]:
        try:
            while chunk := await asyncio.to_thread(output.read, 65536):
                yield chunk
        finally:
            await asyncio.to_thread(output.close)

    return StreamingResponse(
        chunks(),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="studyflow-export.json"',
            "Cache-Control": "no-store",
        },
    )
