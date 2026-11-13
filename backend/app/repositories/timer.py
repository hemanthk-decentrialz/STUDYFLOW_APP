import logging
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.dialects.postgresql import insert

from app.models.course import Course
from app.models.focus_session import FocusSession
from app.models.timer import Timer
from app.repositories.owned import OwnedRepository

logger = logging.getLogger("studyflow.repositories.timer")


class TimerRepository(OwnedRepository):
    async def get(self) -> Timer | None:
        logger.debug("repository_operation operation=get")
        return await self.session.scalar(select(Timer).where(Timer.user_id == self.user_id))

    async def save(self, timer: Timer) -> Timer:
        logger.debug("repository_operation operation=save")
        values = {column.name: getattr(timer, column.name) for column in Timer.__table__.columns}
        statement = insert(Timer).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[Timer.user_id],
            set_={key: value for key, value in values.items() if key != "user_id"},
        ).returning(Timer)
        return (
            await self.session.scalars(statement.execution_options(populate_existing=True))
        ).one()

    async def focus(self, focus_id: UUID) -> FocusSession | None:
        return await self.session.get(FocusSession, (focus_id, self.user_id))

    async def start_focus(
        self, course_id: int | None, start: datetime, end: datetime
    ) -> FocusSession:
        record = FocusSession(
            user_id=self.user_id,
            course_id=course_id,
            started_at=start,
            planned_end_at=end,
            outcome="running",
        )
        self.session.add(record)
        await self.session.flush()
        return record

    @staticmethod
    def seconds(start: datetime, end: datetime) -> ColumnElement[Decimal]:
        actual_end = func.least(
            func.coalesce(FocusSession.ended_at, func.now()), FocusSession.planned_end_at, end
        )
        return func.greatest(
            0, func.extract("epoch", actual_end - func.greatest(FocusSession.started_at, start))
        )

    async def focus_page(
        self, page: int, limit: int, order: str, course_id: int | None
    ) -> tuple[list[tuple[FocusSession, str, int]], int]:
        conditions = [FocusSession.user_id == self.user_id]
        if course_id is not None:
            conditions.append(FocusSession.course_id == course_id)
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(FocusSession).where(*conditions)
            )
            or 0
        )
        duration = func.greatest(
            0,
            func.extract(
                "epoch",
                func.least(
                    func.coalesce(FocusSession.ended_at, func.now()), FocusSession.planned_end_at
                )
                - FocusSession.started_at,
            ),
        )
        statement = (
            select(
                FocusSession,
                func.coalesce(Course.title, "Unassigned").label("title"),
                func.floor(duration).label("seconds"),
            )
            .outerjoin(
                Course, (Course.id == FocusSession.course_id) & (Course.user_id == self.user_id)
            )
            .where(*conditions)
            .order_by(
                FocusSession.started_at.asc() if order == "asc" else FocusSession.started_at.desc(),
                FocusSession.id.desc(),
            )
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return [
            (record, str(title), int(seconds))
            for record, title, seconds in (await self.session.execute(statement)).all()
        ], total

    async def focus_totals(
        self, boundaries: list[datetime]
    ) -> tuple[list[int], list[tuple[int | None, str, int]], int]:
        conditions = [
            FocusSession.user_id == self.user_id,
            FocusSession.started_at < boundaries[-1],
            FocusSession.started_at >= boundaries[0] - timedelta(minutes=120),
            FocusSession.planned_end_at >= boundaries[0],
        ]
        days = (
            await self.session.execute(
                select(
                    *[
                        func.coalesce(func.sum(self.seconds(start, end)), 0).label(f"day{i}")
                        for i, (start, end) in enumerate(zip(boundaries, boundaries[1:]))
                    ],
                    func.count()
                    .filter(
                        FocusSession.outcome == "completed",
                        FocusSession.ended_at >= boundaries[0],
                        FocusSession.ended_at < boundaries[-1],
                    )
                    .label("completed"),
                ).where(*conditions)
            )
        ).one()
        courses = (
            await self.session.execute(
                select(
                    FocusSession.course_id,
                    func.coalesce(Course.title, "Unassigned"),
                    func.floor(func.sum(self.seconds(boundaries[0], boundaries[-1]))).label(
                        "seconds"
                    ),
                )
                .outerjoin(
                    Course, (Course.id == FocusSession.course_id) & (Course.user_id == self.user_id)
                )
                .where(*conditions)
                .group_by(FocusSession.course_id, Course.title)
                .order_by(
                    func.sum(self.seconds(boundaries[0], boundaries[-1])).desc(), Course.title
                )
                .limit(20)
            )
        ).all()
        return (
            [int(seconds) for seconds in days[:-1]],
            [(course_id, str(title), int(seconds)) for course_id, title, seconds in courses],
            int(days[-1]),
        )
