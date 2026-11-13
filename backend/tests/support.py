"""Test-only configuration guards and cookie-aware API helpers."""

from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy.engine import make_url

PASSWORD = "StudyflowTest2026!"
INERT_DATABASE_URL = "postgresql+asyncpg://invalid@127.0.0.1:1/studyflow_test"


def normalize_host(host: str | None) -> str | None:
    return "loopback" if host in {"localhost", "127.0.0.1", "::1"} else host


def validate_test_database(
    value: str, development: str | None = None, *, production: bool = False
) -> str:
    if production:
        raise ValueError("Tests refuse APP_ENV=production.")
    try:
        url = make_url(value)
        port = url.port or 5432
        if url.drivername != "postgresql+asyncpg":
            raise ValueError
        if not url.host or not url.database or not url.database.endswith("_test"):
            raise ValueError
        if url.query:
            raise ValueError
        if development:
            dev = make_url(development)
            if (normalize_host(url.host), port, url.database) == (
                normalize_host(dev.host),
                dev.port or 5432,
                dev.database,
            ):
                raise ValueError
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "Use a separate postgresql+asyncpg database ending in _test, "
            "without URL query options; it must differ from DATABASE_URL."
        ) from exc
    return url.render_as_string(hide_password=False)


@dataclass
class Actor:
    client: httpx.AsyncClient
    user: dict[str, Any]

    async def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        status: int = 200,
        **kwargs: Any,
    ) -> Any:
        response = await self.client.request(method, "/api/v1" + path, json=body, **kwargs)
        assert response.status_code == status, (method, path, response.status_code, response.text)
        if not response.content:
            return None
        payload = response.json()
        if status >= 400:
            assert payload["ok"] is False and "error" in payload
            return payload
        assert payload["ok"] is True
        return payload["data"]

    async def course(self, resource_id: int = 1, title: str = "Postgresql") -> dict[str, Any]:
        return await self.request(
            "POST",
            "/courses",
            {"id": resource_id, "title": title, "description": "Database study"},
            status=201,
        )


async def register(client: httpx.AsyncClient, email: str) -> Actor:
    signup = await client.post(
        "/api/v1/users", json={"name": "Test Student", "email": email, "password": PASSWORD}
    )
    assert signup.status_code == 201, signup.text
    login = await client.post("/api/v1/sessions", json={"email": email, "password": PASSWORD})
    assert login.status_code == 201, login.text
    return Actor(client, signup.json()["data"])
