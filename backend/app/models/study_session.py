from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.ownership import OwnedRecord
from app.models.soft_delete import SoftDeleteRecord


class StudySession(OwnedRecord, SoftDeleteRecord, Base):
    # Date.now() IDs need BIGINT rather than INTEGER.
    goal_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["goal_id", "user_id", "course_id"],
            ["goal.id", "goal.user_id", "goal.course_id"],
            name="fk_study_session_goal_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "user_id"],
            ["course.id", "course.user_id"],
            name="fk_study_session_course_owner",
            ondelete="RESTRICT",
        ),
    )
    course_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    time: Mapped[str] = mapped_column(String(5), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("60")
    )
    priority: Mapped[str] = mapped_column(
        String(6), nullable=False, server_default=text("'Medium'")
    )
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


sa.Index(
    "uq_study_session_owner_active_key",
    StudySession.user_id,
    sa.func.lower(sa.func.btrim(StudySession.subject)),
    sa.func.lower(sa.func.btrim(StudySession.time)),
    unique=True,
    postgresql_where=sa.and_(
        StudySession.deleted_at.is_(None), StudySession.scheduled_date.is_(None)
    ),
)
sa.Index(
    "ix_study_session_owner_active_position",
    StudySession.user_id,
    StudySession.position,
    StudySession.id,
    postgresql_where=StudySession.deleted_at.is_(None),
)
sa.Index(
    "ix_study_session_owner_time_active",
    StudySession.user_id,
    StudySession.time,
    StudySession.id,
    postgresql_where=StudySession.deleted_at.is_(None),
)
sa.Index(
    "uq_study_session_owner_dated_key",
    StudySession.user_id,
    StudySession.scheduled_date,
    sa.func.lower(sa.func.btrim(StudySession.subject)),
    sa.func.lower(sa.func.btrim(StudySession.time)),
    unique=True,
    postgresql_where=sa.and_(
        StudySession.deleted_at.is_(None), StudySession.scheduled_date.is_not(None)
    ),
)
sa.Index(
    "ix_study_session_owner_date_active",
    StudySession.user_id,
    StudySession.scheduled_date,
    StudySession.time,
    StudySession.id,
    postgresql_where=StudySession.deleted_at.is_(None),
)
sa.Index(
    "ix_study_session_owner_course_active",
    StudySession.user_id,
    StudySession.course_id,
    postgresql_where=StudySession.deleted_at.is_(None),
)
sa.Index(
    "ix_study_session_owner_goal_active",
    StudySession.user_id,
    StudySession.goal_id,
    postgresql_where=StudySession.deleted_at.is_(None),
)


sa.Index(
    "ix_study_session_owner_deleted",
    StudySession.user_id,
    StudySession.deleted_at,
    StudySession.id,
    postgresql_where=StudySession.deleted_at.is_not(None),
)
