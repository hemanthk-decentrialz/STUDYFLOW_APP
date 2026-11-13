"""Server-authoritative timer, preferences, export and native reset jobs."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


async def test_timer_conflicts_and_forged_fields(actor):
    timer = await actor.request("GET", "/timers/current")
    assert timer["timeLeft"] == 1500
    started = await actor.request(
        "PATCH",
        "/timers/current",
        {"expectedRevision": timer["revision"], "timer": {"isRunning": True, "timeLeft": 1}},
    )
    assert started["timeLeft"] > 1400  # clients cannot shorten an interval to earn completion
    await actor.request(
        "PATCH",
        "/timers/current",
        {"expectedRevision": timer["revision"], "timer": {"isRunning": False}},
        status=409,
    )
    await actor.request(
        "PATCH",
        "/timers/current",
        {"expectedRevision": started["revision"], "timer": {"completedSessions": 99}},
        status=422,
    )


async def test_completion_recorded_once(actor, db):
    from app.models.focus_session import FocusSession
    from app.models.timer import Timer

    await actor.course()
    await actor.request(
        "PATCH",
        "/timers/current",
        {"expectedRevision": 0, "timer": {"isRunning": True, "courseId": 1}},
    )
    async with AsyncSession(db) as session, session.begin():
        timer = (await session.scalars(select(Timer))).one()
        focus = (await session.scalars(select(FocusSession))).one()
        end = datetime.fromtimestamp(
            int((datetime.now(UTC) - timedelta(seconds=1)).timestamp() * 1000) / 1000, UTC
        )
        focus.started_at = end - timedelta(minutes=25)
        focus.planned_end_at = end
        timer.end_at = int(end.timestamp() * 1000)
    first = await actor.request("GET", "/timers/current")
    second = await actor.request("GET", "/timers/current")
    assert first["completedSessions"] == second["completedSessions"] == 1
    assert first["timeLeft"] == 0 and first["isRunning"] is False
    history = await actor.request("GET", "/focus-sessions")
    assert history["total"] == 1
    assert history["items"][0]["outcome"] == "completed"
    assert history["items"][0]["seconds"] == 1500


async def test_breaks_do_not_create_focus_history(actor):
    await actor.request(
        "PATCH",
        "/timers/current",
        {"expectedRevision": 0, "timer": {"mode": "Short Break", "isRunning": True}},
    )
    assert (await actor.request("GET", "/focus-sessions"))["total"] == 0


async def test_preferences_partial_update_and_export(actor):
    await actor.request(
        "PATCH",
        "/preferences",
        {"settings": {"theme": "dark", "focusMinutes": 40, "timeZone": "Asia/Kolkata"}},
    )
    saved = await actor.request("GET", "/preferences")
    assert saved["theme"] == "dark" and saved["focusMinutes"] == 40
    assert (await actor.request("GET", "/timers/current"))["timeLeft"] == 2400
    await actor.course()
    await actor.request(
        "POST",
        "/notes",
        {"id": 2, "courseId": 1, "title": "Private", "content": "Study"},
        status=201,
    )
    await actor.request("DELETE", "/notes/2", status=204)
    response = await actor.client.get("/api/v1/data-exports")
    assert response.status_code == 200 and "attachment" in response.headers["content-disposition"]
    exported = response.json()
    assert len(exported["notes"]) == 1
    assert "password" not in response.text and "token_hash" not in response.text
    assert "users" not in exported and "authSessions" not in exported


@pytest.mark.parametrize(
    "settings",
    [
        {"focusMinutes": 0},
        {"focusMinutes": 121},
        {"completionSound": "yes"},
        {"timeZone": "Invalid/Zone"},
        {"unknown": 1},
    ],
)
async def test_invalid_preferences(actor, settings):
    await actor.request("PATCH", "/preferences", {"settings": settings}, status=422)


async def test_reset_is_owner_scoped_and_preserves_preferences(actor, another_actor):
    other = await another_actor()
    await actor.course()
    await other.course(1, "Other course")
    await actor.request("PATCH", "/preferences", {"settings": {"theme": "dark"}})
    await actor.request("POST", "/data-resets", status=202)
    job = await actor.request("GET", "/data-resets/current")
    assert job["status"] == "completed"
    assert (await actor.request("GET", "/courses"))["total"] == 0
    assert (await actor.request("GET", "/preferences"))["theme"] == "dark"
    assert (await other.request("GET", "/courses"))["total"] == 1
    assert await actor.request("GET", "/users/me")


async def test_dashboard_reminders_summary_and_health(actor):
    await actor.course()
    summary = await actor.request(
        "GET", "/dashboards/summary", params={"time_zone": "Asia/Kolkata"}
    )
    assert summary["totalNotes"] == 0 and summary["timeZone"] == "Asia/Kolkata"
    assert await actor.request("GET", "/reminders") == []
    focus = await actor.request("GET", "/focus-sessions/summary", params={"time_zone": "UTC"})
    assert focus["seconds"] == 0 and len(focus["days"]) == 7
    response = await actor.client.get("/api/v1/health")
    assert response.status_code == 200


async def test_due_reminder_excludes_completed_sessions(actor):
    await actor.course()
    await actor.request(
        "PATCH",
        "/preferences",
        {"settings": {"sessionReminders": True, "timeZone": "UTC", "reminderLeadMinutes": 15}},
    )
    due = datetime.now(UTC) + timedelta(minutes=10)
    await actor.request(
        "POST",
        "/study-sessions",
        {
            "id": 2,
            "courseId": 1,
            "scheduledDate": due.date().isoformat(),
            "time": due.strftime("%H:%M"),
            "durationMinutes": 30,
            "priority": "Medium",
            "completed": False,
        },
        status=201,
    )
    assert len(await actor.request("GET", "/reminders")) == 1
    await actor.request("PATCH", "/study-sessions/2", {"completed": True})
    assert await actor.request("GET", "/reminders") == []


async def test_application_lifespan_and_migration_metadata(db, monkeypatch):
    import asyncio
    import os
    import subprocess
    import sys
    from unittest.mock import Mock

    from app import main
    from app.core.logging import redact

    listener = Mock()
    monkeypatch.setattr(main, "configure_logging", lambda: listener)
    async with main.app.router.lifespan_context(main.app):
        assert (await main.HealthService().readiness()).status == "ready"
        await asyncio.sleep(0)
    listener.stop.assert_called_once()
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "check"],
        env=dict(os.environ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, redact(result.stdout + result.stderr)
