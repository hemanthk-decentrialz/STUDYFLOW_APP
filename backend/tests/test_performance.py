"""Actual PostgreSQL plans and constant query counts, not a load benchmark."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.performance]


async def test_queries_plans_and_connection_reuse(actor, db, performance_report):
    from app.models.focus_session import FocusSession
    from app.models.goal import Goal
    from app.models.note import Note
    from app.models.study_session import StudySession
    from app.repositories.resources import GoalRepository, NoteRepository, PlannerRepository
    from app.repositories.timer import TimerRepository
    from app.schemas.goals import GoalResponse

    await actor.course()
    owner = UUID(actor.user["id"])
    now = datetime.now(UTC)
    async with AsyncSession(db) as session, session.begin():
        await session.execute(
            insert(Goal),
            [
                {
                    "id": n + 1,
                    "user_id": owner,
                    "course_id": 1,
                    "subject": "Postgresql",
                    "title": f"Goal {n:04}",
                    "deadline": date(2027, 1, 1),
                    "progress": 0,
                    "position": n,
                }
                for n in range(500)
            ],
        )
        await session.execute(
            insert(Note),
            [
                {
                    "id": n + 1,
                    "user_id": owner,
                    "course_id": 1,
                    "subject": "Postgresql",
                    "title": f"Note {n:04}",
                    "content": "searchable study notes",
                    "position": n,
                }
                for n in range(1500)
            ],
        )
        await session.execute(
            insert(StudySession),
            [
                {
                    "id": n + 1,
                    "user_id": owner,
                    "course_id": 1,
                    "goal_id": n % 500 + 1,
                    "subject": "Postgresql",
                    "time": f"{n % 24:02}:{n % 60:02}",
                    "scheduled_date": date(2027, 1, 1) + timedelta(days=n),
                    "duration_minutes": 30,
                    "priority": "Medium",
                    "completed": False,
                    "position": n,
                }
                for n in range(2000)
            ],
        )
        await session.execute(
            insert(FocusSession),
            [
                {
                    "id": uuid4(),
                    "user_id": owner,
                    "course_id": 1,
                    "started_at": now - timedelta(days=n + 1),
                    "planned_end_at": now - timedelta(days=n + 1) + timedelta(minutes=25),
                    "ended_at": now - timedelta(days=n + 1) + timedelta(minutes=25),
                    "outcome": "completed",
                }
                for n in range(50)
            ],
        )
    async with db.begin() as connection:
        for table in ("goal", "note", "study_session", "focus_session"):
            await connection.execute(text("ANALYZE " + table))
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append((statement, parameters))

    event.listen(db.sync_engine, "before_cursor_execute", capture)
    counts = {}
    plans = {}
    try:
        async with AsyncSession(db) as session:
            for limit in (1, 20):
                statements.clear()
                rows, total = await GoalRepository(session, owner).list_page(
                    page=1, limit=limit, search=None, sort_by="position", order="asc", filters={}
                )
                [GoalResponse.model_validate(row) for row in rows]
                assert total == 500 and len(rows) == limit
                counts[f"goals_{limit}"] = len(statements)
                assert len(statements) == 2
                plans["goals"] = statements[-1]
                statements.clear()
                rows, total = await TimerRepository(session, owner).focus_page(
                    1, limit, "desc", None
                )
                assert total == 50 and len(rows) == limit
                counts[f"focus_{limit}"] = len(statements)
                assert len(statements) == 2
                plans["focus"] = statements[-1]
            for label, repository, kwargs in [
                ("notes", NoteRepository(session, owner), {}),
                ("notes_contains_search", NoteRepository(session, owner), {"search": "study"}),
                (
                    "planner_date",
                    PlannerRepository(session, owner),
                    {
                        "filters": {"date_from": date(2027, 6, 1), "date_to": date(2027, 6, 7)},
                        "sort_by": "scheduled_date",
                    },
                ),
            ]:
                statements.clear()
                await repository.list_page(
                    **{
                        "page": 1,
                        "limit": 10,
                        "search": None,
                        "sort_by": "position",
                        "order": "asc",
                        "filters": {},
                        **kwargs,
                    }
                )
                plans[label] = statements[-1]
        event.remove(db.sync_engine, "before_cursor_execute", capture)
        results = {}
        async with db.connect() as connection:
            for label, (sql, params) in plans.items():
                results[label] = (
                    await connection.exec_driver_sql(
                        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, params
                    )
                ).scalar_one()[0]
            indexes = list(
                (
                    await connection.execute(
                        text(
                            "SELECT indexname FROM pg_indexes "
                            "WHERE schemaname='public' ORDER BY indexname"
                        )
                    )
                ).scalars()
            )
            assert "ix_focus_session_owner_started" in indexes
            assert any("owner_date_active" in name for name in indexes)
        baseline = db.pool.checkedout()
        pids = []
        for _ in range(4):
            async with db.connect() as connection:
                pids.append(await connection.scalar(text("SELECT pg_backend_pid()")))
        assert len(set(pids)) == 1 and db.pool.checkedout() == baseline
        performance_report.update(
            dataset={"goals": 500, "notes": 1500, "planner": 2000, "focus": 50},
            query_counts=counts,
            plans=results,
            indexes=indexes,
            pool={
                "size": db.pool.size(),
                "reused_backend": len(set(pids)) == 1,
                "connections_returned": db.pool.checkedout() == baseline,
            },
        )
    finally:
        if event.contains(db.sync_engine, "before_cursor_execute", capture):
            event.remove(db.sync_engine, "before_cursor_execute", capture)
