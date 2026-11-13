import logging

from asyncpg import IntegrityConstraintViolationError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from starlette.exceptions import HTTPException

from app.core.config import get_settings
from app.core.exceptions import ApiError
from app.schemas.api import ApiFailure

logger = logging.getLogger("studyflow.errors")


def failure(status: int, message: str, details: list[str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ApiFailure(error=message, details=details).model_dump(exclude_none=True),
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        },
    )


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    logger.warning(
        "api_error method=%s path=%r status=%s",
        request.method,
        getattr(request.scope.get("route"), "path", "unmatched"),
        exc.status_code,
    )
    response = failure(exc.status_code, exc.message)
    if exc.status_code == 401:
        settings = get_settings()
        response.delete_cookie(
            settings.SESSION_COOKIE_NAME,
            path="/",
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
        )
    return response


async def validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    logger.warning(
        "request_validation_failed method=%s path=%r",
        request.method,
        getattr(request.scope.get("route"), "path", "unmatched"),
    )
    details = [
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
    ]
    # Never log request bodies, invalid password input, or cookie values.
    return failure(422, "Request validation failed.", details)


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    logger.warning(
        "http_error method=%s path=%r status=%s",
        request.method,
        getattr(request.scope.get("route"), "path", "unmatched"),
        exc.status_code,
    )
    response = failure(exc.status_code, str(exc.detail))
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def integrity_error_handler(request: Request, exc: Exception) -> JSONResponse:
    original = exc.orig if isinstance(exc, IntegrityError) else exc
    state = getattr(original, "sqlstate", None)
    logger.warning(
        "integrity_conflict method=%s path=%r sqlstate=%s",
        request.method,
        getattr(request.scope.get("route"), "path", "unmatched"),
        state,
    )
    # get_db's transaction context has already rolled back before this handler runs.
    if state == "23505":
        return failure(409, "An active resource with these unique fields already exists.")
    if state == "23503":
        return failure(409, "A referenced record no longer exists or is not valid.")
    return failure(409, "This change conflicts with the database constraints.")


async def database_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "database_error method=%s path=%r kind=%s",
        request.method,
        getattr(request.scope.get("route"), "path", "unmatched"),
        type(exc).__name__,
    )
    return failure(503, "The database operation could not be completed. Please try again later.")


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_error method=%s path=%r",
        request.method,
        getattr(request.scope.get("route"), "path", "unmatched"),
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={"request_id": request.scope.get("request_id", "-")},
    )
    response = failure(500, "An unexpected server error occurred.")
    response.headers["X-Request-ID"] = request.scope.get("request_id", "-")
    origin = request.headers.get("origin")
    if origin in get_settings().request_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(IntegrityConstraintViolationError, integrity_error_handler)
    for error_type in (OperationalError, SQLAlchemyTimeoutError, ConnectionError, TimeoutError):
        app.add_exception_handler(error_type, database_error_handler)
    for error_type in (
        DBAPIError,
        SQLAlchemyError,
        ValidationError,
        ResponseValidationError,
        Exception,
    ):
        app.add_exception_handler(error_type, unhandled_error_handler)
