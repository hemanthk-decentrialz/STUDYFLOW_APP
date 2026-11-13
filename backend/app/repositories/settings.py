import logging
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    Time,
    cast,
    delete,
    func,
    literal,
    select,
    union_all,
)
from sqlalchemy.dialects.postgresql import insert

from app.models.course import Course
from app.models.focus_session import FocusSession
from app.models.goal import Goal
from app.models.note import Note
from app.models.settings import Settings
from app.models.study_session import StudySession
from app.models.timer import Timer
from app.repositories.owned import OwnedRepository

logger = logging.getLogger("studyflow.repositories.settings")


class SettingsRepository(OwnedRepository):
    async def get(self) -> Settings | None:
        logger.debug("repository_operation operation=get")
        return await self.session.scalar(select(Settings).where(Settings.user_id == self.user_id))

    async def save(self, settings: Settings) -> Settings:
        logger.debug("repository_operation operation=save")
        statement = insert(Settings).values(
            user_id=self.user_id, theme=settings.theme, preferences=settings.preferences
        )
        statement = statement.on_conflict_do_update(
            index_elements=[Settings.user_id],
            set_={"theme": settings.theme, "preferences": settings.preferences},
        ).returning(Settings)
        return (
            await self.session.scalars(statement.execution_options(populate_existing=True))
        ).one()

    async def reset_study_data(self, *, allow_reset: bool = False) -> None:
        logger.debug("repository_operation operation=reset_study_data")
        await self.lock_owner(allow_reset=allow_reset)
        for model in (Timer, FocusSession, StudySession, Note, Goal, Course):
            await self.session.execute(delete(model).where(model.user_id == self.user_id))
        await self.session.flush()

    async def deleted_page(
        self, page: int, limit: int, kind: str | None, search: str | None, order: str
    ) -> tuple[list[dict[str, Any]], int]:
        branches = []
        for name, model in (
            ("courses", Course),
            ("notes", Note),
            ("goals", Goal),
            ("study-sessions", StudySession),
        ):
            if kind and kind != name:
                continue
            title = model.subject if model is StudySession else model.title
            branches.append(
                select(
                    literal(name).label("kind"),
                    model.id,
                    title.label("title"),
                    model.deleted_at.label("deletedAt"),
                    (cast(literal(None), BigInteger) if model is Course else model.course_id).label(
                        "courseId"
                    ),
                ).where(model.user_id == self.user_id, model.deleted_at.is_not(None))
            )
        records = union_all(*branches).subquery()
        conditions = [records.c.title.ilike(f"%{search}%")] if search else []
        total = int(
            await self.session.scalar(select(func.count()).select_from(records).where(*conditions))
            or 0
        )
        statement = (
            select(records)
            .where(*conditions)
            .order_by(
                records.c.deletedAt.asc() if order == "asc" else records.c.deletedAt.desc(),
                records.c.kind,
                records.c.id,
            )
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return [dict(row) for row in (await self.session.execute(statement)).mappings()], total

    async def export_rows(self, model: type) -> AsyncIterator[dict[str, Any]]:
        # Column projections omit ORM relationship/computed loads; each batch stays bounded.
        columns = [column for column in model.__table__.columns if column.name != "user_id"]
        result = await self.session.stream(
            select(*columns).where(model.user_id == self.user_id).execution_options(yield_per=100)
        )
        try:
            async for row in result.mappings():
                yield dict(row)
        finally:
            await result.close()

    async def due_reminders(
        self, now: datetime, zone: str, lead: int, sessions: bool, goals: bool
    ) -> list[dict[str, Any]]:
        first_date = (now - timedelta(minutes=1)).astimezone(ZoneInfo(zone)).date()
        last_date = (now + timedelta(minutes=lead)).astimezone(ZoneInfo(zone)).date()
        branches = []
        if sessions:
            due = func.timezone(zone, StudySession.scheduled_date + cast(StudySession.time, Time))
            branches.append(
                select(
                    literal("study-sessions").label("kind"),
                    cast(StudySession.id, String).label("id"),
                    StudySession.subject.label("title"),
                    due.label("dueAt"),
                ).where(
                    StudySession.user_id == self.user_id,
                    StudySession.deleted_at.is_(None),
                    StudySession.completed.is_(False),
                    StudySession.scheduled_date.between(first_date, last_date),
                    due >= now - timedelta(minutes=1),
                    due <= now + timedelta(minutes=lead),
                )
            )
        if goals:
            due = func.timezone(zone, cast(Goal.deadline, DateTime) + timedelta(hours=9))
            branches.append(
                select(
                    literal("goals").label("kind"),
                    cast(Goal.id, String).label("id"),
                    Goal.title,
                    due.label("dueAt"),
                ).where(
                    Goal.user_id == self.user_id,
                    Goal.deleted_at.is_(None),
                    Goal.progress < 100,
                    Goal.deadline.between(first_date, last_date),
                    due >= now - timedelta(minutes=1),
                    due <= now + timedelta(minutes=lead),
                )
            )
        if not branches:
            return []
        rows = union_all(*branches).subquery()
        return [
            dict(row)
            for row in (
                await self.session.execute(
                    select(rows).order_by(rows.c.dueAt, rows.c.kind, rows.c.id).limit(100)
                )
            ).mappings()
        ]
