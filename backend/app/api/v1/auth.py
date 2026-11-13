from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.dependencies import CurrentUser, get_auth_service
from app.core.config import get_settings
from app.schemas.api import ApiSuccess
from app.schemas.auth import LoginRequest, ProfilePatch, SessionUser, SignupRequest
from app.services.auth import AuthService

router = APIRouter(tags=["authentication"])
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=ApiSuccess[SessionUser])
async def signup(payload: SignupRequest, service: AuthServiceDependency) -> ApiSuccess[SessionUser]:
    # SignupForm redirects to login rather than auto-authenticating.
    return ApiSuccess(ok=True, data=await service.signup(payload))


@router.post(
    "/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiSuccess[SessionUser],
    summary="Create a secure cookie session",
)
async def login(
    payload: LoginRequest, request: Request, response: Response, service: AuthServiceDependency
) -> ApiSuccess[SessionUser]:
    settings = get_settings()
    user, token = await service.login(payload, request.cookies.get(settings.SESSION_COOKIE_NAME))
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return ApiSuccess(ok=True, data=user)


@router.get("/users/me", response_model=ApiSuccess[SessionUser])
async def me(user: CurrentUser) -> ApiSuccess[SessionUser]:
    return ApiSuccess(ok=True, data=user)


@router.patch(
    "/users/me",
    response_model=ApiSuccess[SessionUser],
    summary="Update the current account's display name",
)
async def update_profile(
    payload: ProfilePatch, user: CurrentUser, service: AuthServiceDependency
) -> ApiSuccess[SessionUser]:
    return ApiSuccess(ok=True, data=await service.update_profile(user, payload))


@router.delete(
    "/sessions/current",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current cookie session",
)
async def logout(request: Request, response: Response, service: AuthServiceDependency) -> Response:
    settings = get_settings()
    await service.logout(request.cookies.get(settings.SESSION_COOKIE_NAME))
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
