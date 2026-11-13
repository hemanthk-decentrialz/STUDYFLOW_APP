"""Fast validation, privacy, async utility and isolated service checks."""

import json
import logging
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.support import validate_test_database

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///studyflow_test",
        "postgresql+asyncpg://u@localhost/studyflow",
        "postgresql+asyncpg://u@localhost/studyflow_test?x=y",
    ],
)
def test_database_guard_rejects_unsafe_targets(url):
    with pytest.raises(ValueError):
        validate_test_database(url)


def test_database_guard_rejects_alias_and_production():
    with pytest.raises(ValueError):
        validate_test_database(
            "postgresql+asyncpg://a@127.0.0.1/app_test", "postgresql+asyncpg://b@localhost/app_test"
        )
    with pytest.raises(ValueError):
        validate_test_database("postgresql+asyncpg://a@localhost/app_test", production=True)
    assert validate_test_database("postgresql+asyncpg://a@localhost/app_test").endswith("app_test")


@pytest.mark.parametrize(
    "payload",
    [{"limit": 101}, {"page": 1001, "limit": 100}, {"sort_by": "DROP TABLE note"}, {"unknown": 1}],
)
def test_query_bounds(payload):
    from app.schemas.resources import NoteListParams

    with pytest.raises(ValidationError):
        NoteListParams.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"expectedVersion": 1},
        {"expectedVersion": 1, "content": None},
        {"content": "text"},
        {"expectedVersion": 1, "content": "   "},
    ],
)
def test_note_patch_validation(payload):
    from app.schemas.notes import NotePatch

    with pytest.raises(ValidationError):
        NotePatch.model_validate(payload)


def test_structured_logging_masks_credentials():
    from app.core.logging import JsonFormatter, PrivacyFilter

    message = "password=Secret123 cookie=abc email=student@example.com postgresql://admin:pass@localhost/db"
    record = logging.LogRecord("studyflow", logging.ERROR, __file__, 1, message, (), None)
    PrivacyFilter().filter(record)
    output = JsonFormatter().format(record)
    assert json.loads(output)["level"] == "ERROR"
    for secret in ["Secret123", "student@example.com", "admin:pass", "cookie=abc"]:
        assert secret not in output


async def test_password_hashing_uses_worker_thread(monkeypatch):
    from app.core import security

    main_thread = threading.get_ident()

    def hash_in_worker(value):
        assert threading.get_ident() != main_thread
        return "hashed:" + value

    monkeypatch.setattr(security, "password_hasher", SimpleNamespace(hash=hash_in_worker))
    assert await security.hash_password("example") == "hashed:example"


async def test_stale_note_service_never_writes():
    from app.core.exceptions import ApiError
    from app.schemas.notes import NotePatch
    from app.services.resources import NoteService

    repository = SimpleNamespace(
        lock_owner=AsyncMock(),
        get=AsyncMock(return_value=SimpleNamespace(version=2)),
        update=AsyncMock(),
    )
    with pytest.raises(ApiError) as error:
        await NoteService(repository).patch_resource(
            1, NotePatch(expectedVersion=1, content="changed")
        )
    assert error.value.status_code == 409
    repository.update.assert_not_awaited()


def test_testclient_no_database_smoke():
    from app.main import app

    # No context manager: this smoke check intentionally does not start DB lifespan jobs.
    client = TestClient(app)
    response = client.get("/api/v1/not-a-route")
    assert response.status_code == 404
    assert response.json()["ok"] is False
    client.close()


async def test_rate_limit_is_enforced(monkeypatch):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.core import rate_limit

    monkeypatch.setattr(
        rate_limit,
        "get_settings",
        lambda: SimpleNamespace(
            RATE_LIMIT_DEFAULT="2/minute",
            RATE_LIMIT_AUTH="2/minute",
            RATE_LIMIT_SIGNUP="2/minute",
            RATE_LIMIT_RESETS="2/minute",
        ),
    )
    application = FastAPI()
    application.add_middleware(rate_limit.RateLimitMiddleware)

    @application.get("/api/v1/example")
    async def example():
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://localhost"
    ) as api:
        assert (await api.get("/api/v1/example")).status_code == 200
        assert (await api.get("/api/v1/example")).status_code == 200
        response = await api.get("/api/v1/example")
        assert response.status_code == 429 and int(response.headers["retry-after"]) > 0


async def test_unhandled_error_is_sanitized():
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.core.error_handlers import register_error_handlers

    application = FastAPI()
    register_error_handlers(application)

    @application.get("/error")
    async def error():
        raise RuntimeError("password=never-expose-this")

    async with AsyncClient(
        transport=ASGITransport(app=application, raise_app_exceptions=False),
        base_url="http://localhost",
    ) as api:
        response = await api.get("/error")
        assert response.status_code == 500
        assert "never-expose" not in response.text and "RuntimeError" not in response.text
