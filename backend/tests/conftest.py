"""No application database is imported until the test target has been isolated."""

import asyncio
import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from dotenv import dotenv_values
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.support import INERT_DATABASE_URL, Actor, register, validate_test_database

ROOT = Path(__file__).resolve().parents[1]
original_url = os.environ.get("DATABASE_URL") or dotenv_values(ROOT / ".env").get("DATABASE_URL")
was_production = os.environ.get("APP_ENV") == "production"
TEST_URL = os.environ.get("TEST_DATABASE_URL") or dotenv_values(ROOT / ".env.test").get(
    "TEST_DATABASE_URL"
)
CONFIG_ERROR: str | None = None
safe_url = INERT_DATABASE_URL
if TEST_URL:
    try:
        safe_url = validate_test_database(TEST_URL, original_url, production=was_production)
    except ValueError as exc:
        CONFIG_ERROR = str(exc)
# Even unit-only collection cannot accidentally initialize the app against .env's database.
os.environ.update(
    DATABASE_URL=safe_url,
    APP_ENV="development",
    DOCS_ENABLED="true",
    COOKIE_SECURE="false",
    SESSION_COOKIE_NAME="studyflow_session",
    API_ORIGIN="http://localhost:8000",
    TRUSTED_HOSTS='["localhost","127.0.0.1","testserver"]',
    ALLOWED_ORIGINS='["http://localhost:3000"]',
    RATE_LIMIT_DEFAULT="100000/minute",
    RATE_LIMIT_AUTH="100000/minute",
    RATE_LIMIT_SIGNUP="100000/hour",
    RATE_LIMIT_RESETS="100000/hour",
    DB_POOL_SIZE="3",
    DB_MAX_OVERFLOW="0",
    DB_POOL_TIMEOUT="2",
    LOG_LEVEL="ERROR",
)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--require-db",
        action="store_true",
        help="Fail rather than skip when TEST_DATABASE_URL is missing.",
    )
    parser.addoption("--performance-report", help="Write measured query/EXPLAIN results as JSON.")


@pytest.fixture(scope="session")
def performance_report(request: pytest.FixtureRequest) -> Iterator[dict[str, Any]]:
    report: dict[str, Any] = {}
    yield report
    destination = request.config.getoption("--performance-report")
    if destination:
        path = Path(destination).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")


@pytest_asyncio.fixture(scope="session")
async def db_engine(request: pytest.FixtureRequest) -> AsyncIterator[AsyncEngine]:
    if CONFIG_ERROR:
        raise pytest.UsageError(CONFIG_ERROR)
    if not TEST_URL:
        if request.config.getoption("--require-db"):
            raise pytest.UsageError(
                "Set TEST_DATABASE_URL or backend/.env.test before --require-db."
            )
        pytest.skip(
            "PostgreSQL tests need TEST_DATABASE_URL; use --require-db to enforce a full run."
        )
    target = validate_test_database(TEST_URL, original_url, production=was_production)
    from app.db.session import engine

    async with engine.connect() as lock:
        actual = await lock.scalar(text("SELECT current_database()"))
        if actual != make_url(target).database:
            raise pytest.UsageError("Connected database does not match the guarded test target.")
        acquired = await lock.scalar(text("SELECT pg_try_advisory_lock(531184203)"))
        await lock.commit()
        if not acquired:
            raise pytest.UsageError(
                "Another Studyflow suite owns this test database; parallel runs are disabled."
            )
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=ROOT,
                env={**os.environ, "DATABASE_URL": target},
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode:
                from app.core.logging import redact

                pytest.fail("Test migration failed: " + redact(result.stdout + result.stderr))
            yield engine
        finally:
            await lock.execute(text("SELECT pg_advisory_unlock(531184203)"))
            await lock.commit()
    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine: AsyncEngine) -> AsyncIterator[AsyncEngine]:
    from app.db.base import Base

    names = ", ".join(
        "public." + db_engine.dialect.identifier_preparer.quote(table.name)
        for table in Base.metadata.sorted_tables
    )

    async def clear() -> None:
        validate_test_database(str(TEST_URL), original_url, production=was_production)
        async with db_engine.begin() as connection:
            assert (
                await connection.scalar(text("SELECT current_database()"))
                == make_url(str(TEST_URL)).database
            )
            await connection.execute(text("TRUNCATE TABLE " + names + " RESTART IDENTITY CASCADE"))

    await clear()
    try:
        yield db_engine
    finally:
        await clear()


@pytest_asyncio.fixture
async def client(db: AsyncEngine) -> AsyncIterator[httpx.AsyncClient]:
    from app.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000"
    ) as instance:
        yield instance


@pytest_asyncio.fixture
async def actor(client: httpx.AsyncClient) -> Actor:
    return await register(client, "student@example.com")


@pytest_asyncio.fixture
async def another_actor(db: AsyncEngine) -> AsyncIterator[Callable[..., Any]]:
    from app.main import app

    async with AsyncExitStack() as stack:

        async def create(email: str = "other@example.com") -> Actor:
            instance = await stack.enter_async_context(
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000"
                )
            )
            return await register(instance, email)

        yield create
