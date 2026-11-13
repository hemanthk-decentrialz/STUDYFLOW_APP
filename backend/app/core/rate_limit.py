import logging

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.error_handlers import failure

logger = logging.getLogger("studyflow.rate_limits")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """SlowAPI 0.1.9 checks use per-process in-memory storage.

    The private check API is the same one used by SlowAPI's own middleware;
    the dependency is pinned because this adapter must be reviewed on upgrade.
    Application limits avoid per-ID bucket bypass and lazy-router discovery.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        settings = get_settings()
        self.limiters = {
            name: Limiter(
                key_func=get_remote_address,
                application_limits=[rule],
                storage_uri="memory://",
                key_prefix=f"studyflow:{name}",
                headers_enabled=False,
                swallow_errors=False,
                in_memory_fallback_enabled=False,
            )
            for name, rule in {
                "api": settings.RATE_LIMIT_DEFAULT,
                "login": settings.RATE_LIMIT_AUTH,
                "signup": settings.RATE_LIMIT_SIGNUP,
                "resets": settings.RATE_LIMIT_RESETS,
            }.items()
        }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if (
            request.method == "OPTIONS"
            or not path.startswith("/api/v1/")
            or path == "/api/v1/health"
        ):
            return await call_next(request)
        names = ["api"]
        if request.method == "POST":
            names += {
                "/api/v1/sessions": ["login"],
                "/api/v1/users": ["signup"],
                "/api/v1/data-resets": ["resets"],
            }.get(path, [])
        try:
            for name in names:
                await run_in_threadpool(
                    self.limiters[name]._check_request_limit, request, None, True
                )
        except RateLimitExceeded as exc:
            logger.warning("rate_limit_exceeded category=%s", names[-1])
            response = failure(429, "Too many requests. Please try again later.")
            if exc.limit is not None:
                response.headers["Retry-After"] = str(exc.limit.limit.get_expiry())
            return response
        except Exception:
            logger.error("rate_limit_storage_unavailable fail_closed=true")
            return failure(503, "Request protection is temporarily unavailable.")
        return await call_next(request)
