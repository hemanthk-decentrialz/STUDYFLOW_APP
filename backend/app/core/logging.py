import copy
import json
import logging
import logging.handlers
import queue
import re
import sys
import traceback
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import cast

from app.core.config import get_settings

request_id: ContextVar[str] = ContextVar("request_id", default="-")


def redact(value: str) -> str:
    value = re.sub(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s/@]+(?::[^\s/@]*)?@", "[REDACTED-URI]@", value)
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED-EMAIL]", value)
    value = re.sub(
        r"(?i)([\"']?(?:password(?:_hash)?|authorization|cookie|token|secret|api_key|email|phone|name)[\"']?\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
        r"\1[REDACTED]",
        value,
    )
    value = re.sub(r"(?i)Bearer\s+\S+", "Bearer [REDACTED]", value)
    value = re.sub(r"\$argon2\S+", "[REDACTED-HASH]", value)
    value = re.sub(r"(?<![\w-])[A-Za-z0-9_-]{40,}(?![\w-])", "[REDACTED-TOKEN]", value)
    return value


class PrivacyFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        record.request_id = getattr(record, "request_id", request_id.get())
        if record.exc_info:
            record.exc_text = redact("".join(traceback.format_exception(*record.exc_info)))
            record.exc_info = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": redact(record.getMessage()),
        }
        if record.exc_text:
            data["exception"] = redact(record.exc_text)
        return json.dumps(data, ensure_ascii=False)


class NonBlockingLogHandler(logging.handlers.QueueHandler):
    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        return copy.copy(record)

    def enqueue(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            # Logging backpressure must not stop the application event loop.
            pass


class DrainingQueueListener(logging.handlers.QueueListener):
    def enqueue_sentinel(self) -> None:
        # stop() runs in a threadpool; a full queue may drain before shutdown.
        cast(queue.Queue[object], self.queue).put(getattr(self, "_sentinel"))


def configure_logging() -> logging.handlers.QueueListener:
    settings = get_settings()
    output = logging.StreamHandler(sys.stdout)
    output.setFormatter(
        JsonFormatter()
        if settings.APP_ENV == "production"
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    records: queue.Queue[logging.LogRecord] = queue.Queue(maxsize=10000)
    handler = NonBlockingLogHandler(records)
    handler.addFilter(PrivacyFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.LOG_LEVEL)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        child = logging.getLogger(name)
        child.handlers.clear()
        child.propagate = True
        if name in {"uvicorn.access", "sqlalchemy.engine"}:
            child.setLevel(logging.WARNING)
    listener = DrainingQueueListener(records, output, respect_handler_level=True)
    listener.start()
    return listener
