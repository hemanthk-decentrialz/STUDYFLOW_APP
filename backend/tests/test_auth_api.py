"""Real cookie sessions, validation, CORS and ownership boundaries."""

import pytest
from sqlalchemy import select

from tests.support import PASSWORD

pytestmark = pytest.mark.integration


async def test_signup_login_cookie_digest_and_logout(actor, db):
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.security import digest_session_token
    from app.models.auth_session import AuthSession

    token = actor.client.cookies.get("studyflow_session")
    assert token
    async with AsyncSession(db) as session:
        record = (await session.scalars(select(AuthSession))).one()
        assert digest_session_token(token) in [
            getattr(record, c.name) for c in record.__table__.columns
        ]
        assert token not in [getattr(record, c.name) for c in record.__table__.columns]
    login = await actor.client.post(
        "/api/v1/sessions", json={"email": "student@example.com", "password": PASSWORD}
    )
    cookie = login.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "max-age" not in cookie
    me = await actor.request("GET", "/users/me")
    assert "password" not in str(me)
    await actor.request("DELETE", "/sessions/current", status=204)
    await actor.request("GET", "/users/me", status=401)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": "A", "email": "bad", "password": "weak"},
        {"name": "A", "email": "valid@example.com", "password": "short"},
    ],
)
async def test_invalid_signup(client, body):
    response = await client.post("/api/v1/users", json=body)
    assert response.status_code == 422
    assert response.json()["ok"] is False


async def test_duplicate_email_and_bad_login(actor):
    await actor.request(
        "POST",
        "/users",
        {"name": "Other", "email": "student@example.com", "password": PASSWORD},
        status=409,
    )
    await actor.request(
        "POST",
        "/sessions",
        {"email": "student@example.com", "password": "WrongPassword123!"},
        status=401,
    )
    # A 401 deliberately clears the browser cookie; authenticate again before a write.
    await actor.request(
        "POST", "/sessions", {"email": "student@example.com", "password": PASSWORD}, status=201
    )
    await actor.course()


@pytest.mark.parametrize(
    "path",
    [
        "/users/me",
        "/courses",
        "/notes",
        "/goals",
        "/study-sessions",
        "/preferences",
        "/timers/current",
        "/focus-sessions",
        "/data-exports",
    ],
)
async def test_protected_routes(client, path):
    response = await client.get("/api/v1" + path)
    assert response.status_code == 401


async def test_cors_and_untrusted_origin(actor):
    response = await actor.client.options(
        "/api/v1/notes",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"
    response = await actor.client.post(
        "/api/v1/courses",
        json={"id": 1, "title": "SQL"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403


async def test_owner_isolation(actor, another_actor):
    await actor.course()
    other = await another_actor()
    for method, path, body in [
        ("GET", "/courses/1", None),
        ("PATCH", "/courses/1", {"title": "stolen"}),
        ("DELETE", "/courses/1", None),
        ("POST", "/courses/1/restore", None),
    ]:
        await other.request(method, path, body, status=404)
    await other.request(
        "POST", "/notes", {"id": 1, "courseId": 1, "title": "No", "content": "No"}, status=404
    )
    assert (await other.request("GET", "/courses"))["total"] == 0


async def test_expired_cookie_session(actor, db):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.auth_session import AuthSession

    async with AsyncSession(db) as session, session.begin():
        await session.execute(
            update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    await actor.request("GET", "/users/me", status=401)
    assert not actor.client.cookies.get("studyflow_session")


async def test_database_integrity_error_rolls_back(actor, db):
    from uuid import UUID

    from fastapi import Depends, FastAPI
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.error_handlers import register_error_handlers
    from app.db.session import get_db
    from app.models.course import Course

    await actor.course()
    isolated = FastAPI()
    register_error_handlers(isolated)

    @isolated.post("/conflict")
    async def conflict(session: AsyncSession = Depends(get_db, scope="function")):
        session.add(
            Course(
                id=1, user_id=UUID(actor.user["id"]), title="Duplicate", description="", position=1
            )
        )
        await session.flush()

    async with AsyncClient(
        transport=ASGITransport(app=isolated), base_url="http://localhost"
    ) as api:
        response = await api.post("/conflict")
    assert response.status_code == 409
    assert "INSERT" not in response.text and "Duplicate" not in response.text
    assert (await actor.request("GET", "/courses"))["total"] == 1
    await actor.course(2, "Still usable")


async def test_concurrent_duplicate_creation(actor):
    import asyncio

    responses = await asyncio.gather(
        *[
            actor.client.post(
                "/api/v1/courses", json={"id": n, "title": "Same title", "description": ""}
            )
            for n in (1, 2)
        ]
    )
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert (await actor.request("GET", "/courses"))["total"] == 1
