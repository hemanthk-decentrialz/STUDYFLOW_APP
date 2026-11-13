import logging
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.core.error_handlers import failure
from app.core.logging import request_id

logger = logging.getLogger("studyflow.requests")


class RequestPolicyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.max_bytes = get_settings().MAX_REQUEST_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        scope["request_id"] = str(uuid4())
        context = request_id.set(scope["request_id"])
        started = perf_counter()
        request = Request(scope)
        try:
            body = bytearray()
            # Consume a bounded body to prevent unbounded JSON buffering below us.
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > self.max_bytes:
                    await failure(413, "Request body is too large.")(scope, receive, send)
                    return
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False

            async def replay() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            async def secured_send(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    headers["X-Request-ID"] = request_id.get()
                    headers["X-Content-Type-Options"] = "nosniff"
                    headers["X-Frame-Options"] = "DENY"
                    headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                    headers["Cache-Control"] = "no-store"
                    if get_settings().APP_ENV == "production":
                        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                    route = getattr(scope.get("route"), "path", "unmatched")
                    logger.info(
                        "request_finished method=%s route=%s status=%s duration_ms=%.1f",
                        request.method,
                        route,
                        message["status"],
                        (perf_counter() - started) * 1000,
                    )
                await send(message)

            logger.info("request_started method=%s", request.method)
            await self.app(scope, replay, secured_send)
        finally:
            request_id.reset(context)
