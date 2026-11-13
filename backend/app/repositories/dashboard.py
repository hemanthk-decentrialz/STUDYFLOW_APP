import logging
from datetime import date, timedelta
from typing import TypedDict

from sqlalchemy import case, func, select

from app.models.goal import Goal
from app.models.note import Note
from app.models.study_session import StudySession
from app.models.timer import Timer
from app.repositories.owned import OwnedRepository

logger = logging.getLogger("studyflow.repositories.dashboard")


class TodayCounts(TypedDict):
    total: int
    completed: int
    minutes: int
    undated: int


class TodayData(TypedDict):
    counts: TodayCounts
    sessions: list[StudySession]
    next_session: StudySession | None
    goals: list[Goal]
    overdue: int


class DashboardRepository(OwnedRepository):
    async def summary_counts(self) -> dict[str, int | str]:
        logger.debug("repository_operation operation=summary_counts")
        # One SQL statement gives a consistent summary snapshot for this user.
        statement = select(
            select(func.count())
            .select_from(StudySession)
            .where(StudySession.user_id == self.user_id, StudySession.deleted_at.is_(None))
            .scalar_subquery()
            .label("planner"),
            select(func.count())
            .select_from(StudySession)
            .where(
                StudySession.user_id == self.user_id,
                StudySession.deleted_at.is_(None),
                StudySession.completed.is_(True),
            )
            .scalar_subquery()
            .label("completed_planner"),
            select(func.count())
            .select_from(Goal)
            .where(Goal.user_id == self.user_id, Goal.deleted_at.is_(None))
            .scalar_subquery()
            .label("goals"),
            select(func.count())
            .select_from(Goal)
            .where(Goal.user_id == self.user_id, Goal.deleted_at.is_(None), Goal.progress >= 100)
            .scalar_subquery()
            .label("completed_goals"),
            select(func.count())
            .select_from(Note)
            .where(Note.user_id == self.user_id, Note.deleted_at.is_(None))
            .scalar_subquery()
            .label("notes"),
            func.coalesce(
                select(Timer.completed_sessions)
                .where(Timer.user_id == self.user_id)
                .scalar_subquery(),
                0,
            ).label("sessions"),
            func.coalesce(
                select(Goal.title)
                .where(Goal.user_id == self.user_id, Goal.deleted_at.is_(None), Goal.progress < 100)
                .order_by(Goal.position, Goal.id)
                .limit(1)
                .scalar_subquery(),
                "No active goal",
            ).label("active_goal"),
        )
        row = (await self.session.execute(statement)).one()._mapping
        return {
            "planner": int(row["planner"]),
            "completed_planner": int(row["completed_planner"]),
            "goals": int(row["goals"]),
            "completed_goals": int(row["completed_goals"]),
            "notes": int(row["notes"]),
            "sessions": int(row["sessions"]),
            "active_goal": str(row["active_goal"]),
        }

    async def today_data(self, today: date, current_time: str) -> TodayData:
        owned = (StudySession.user_id == self.user_id, StudySession.deleted_at.is_(None))
        counts = (
            (
                await self.session.execute(
                    select(
                        func.count().filter(StudySession.scheduled_date == today).label("total"),
                        func.count()
                        .filter(
                            StudySession.scheduled_date == today, StudySession.completed.is_(True)
                        )
                        .label("completed"),
                        func.coalesce(
                            func.sum(StudySession.duration_minutes).filter(
                                StudySession.scheduled_date == today
                            ),
                            0,
                        ).label("minutes"),
                        func.count().filter(StudySession.scheduled_date.is_(None)).label("undated"),
                    ).where(*owned)
                )
            )
            .one()
            ._mapping
        )
        sessions = list(
            (
                await self.session.scalars(
                    select(StudySession)
                    .where(*owned, StudySession.scheduled_date == today)
                    .order_by(StudySession.time, StudySession.id)
                    .limit(6)
                )
            ).all()
        )
        next_session = await self.session.scalar(
            select(StudySession)
            .where(*owned, StudySession.completed.is_(False), StudySession.scheduled_date >= today)
            .order_by(
                case(
                    (
                        (StudySession.scheduled_date == today)
                        & (StudySession.time >= current_time),
                        0,
                    ),
                    (StudySession.scheduled_date == today, 1),
                    else_=2,
                ),
                StudySession.scheduled_date,
                StudySession.time,
                StudySession.id,
            )
            .limit(1)
        )
        goals_owned = (Goal.user_id == self.user_id, Goal.deleted_at.is_(None), Goal.progress < 100)
        goals = list(
            (
                await self.session.scalars(
                    select(Goal)
                    .where(
                        *goals_owned,
                        Goal.deadline >= today,
                        Goal.deadline <= today + timedelta(days=7),
                    )
                    .order_by(Goal.deadline, Goal.id)
                    .limit(4)
                )
            ).all()
        )
        overdue = await self.session.scalar(
            select(func.count()).select_from(Goal).where(*goals_owned, Goal.deadline < today)
        )
        return {
            "counts": TodayCounts(
                total=int(counts["total"]),
                completed=int(counts["completed"]),
                minutes=int(counts["minutes"]),
                undated=int(counts["undated"]),
            ),
            "sessions": sessions,
            "next_session": next_session,
            "goals": goals,
            "overdue": overdue or 0,
        }
