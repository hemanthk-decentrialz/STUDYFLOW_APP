import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestPolicyMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import engine
from app.services.health import HealthService
from app.tasks.resets import recover_pending_jobs

logger = logging.getLogger("studyflow.lifecycle")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    listener = configure_logging()
    recovery: asyncio.Task[None] | None = None
    try:
        readiness = await HealthService().readiness()
        if get_settings().APP_ENV == "production" and readiness.status != "ready":
            logger.critical("required_startup_dependency_unavailable")
            raise RuntimeError("Required application dependencies are unavailable.")
        recovery = asyncio.create_task(recover_pending_jobs())
        logger.info("application_started environment=%s", get_settings().APP_ENV)
        yield
    finally:
        if recovery:
            recovery.cancel()
            with suppress(asyncio.CancelledError):
                await recovery
        await engine.dispose()
        logger.info("application_stopped")
        await run_in_threadpool(listener.stop)


settings = get_settings()
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
    description=(
        "Cookie-authenticated, owner-scoped student productivity API. "
        "All writes are transactional; list queries are database-side and bounded."
    ),
    docs_url="/api/v1/docs" if settings.DOCS_ENABLED else None,
    redoc_url=None,
    openapi_url="/api/v1/openapi.json" if settings.DOCS_ENABLED else None,
)
app.include_router(api_router)
register_error_handlers(app)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)
app.add_middleware(RequestPolicyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.request_origins,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
    expose_headers=["X-Request-ID", "Retry-After", "Location"],
)
