from datetime import date, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import BigInteger, Date, Integer, String
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.db.base_class import Base
from app.models.ownership import OwnedRecord
from app.models.soft_delete import SoftDeleteRecord
from app.models.study_session import StudySession


class Goal(OwnedRecord, SoftDeleteRecord, Base):
    if TYPE_CHECKING:
        linked_session_count: Mapped[int]
        completed_session_count: Mapped[int]
    __table_args__ = (
        sa.UniqueConstraint("id", "user_id", "course_id", name="uq_goal_id_owner_course"),
        sa.ForeignKeyConstraint(
            ["course_id", "user_id"],
            ["course.id", "course.user_id"],
            name="fk_goal_course_owner",
            ondelete="RESTRICT",
        ),
    )
    course_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


sa.Index(
    "uq_goal_owner_active_key",
    Goal.user_id,
    sa.func.lower(sa.func.btrim(Goal.title)),
    unique=True,
    postgresql_where=Goal.deleted_at.is_(None),
)
sa.Index(
    "ix_goal_owner_active_position",
    Goal.user_id,
    Goal.position,
    Goal.id,
    postgresql_where=Goal.deleted_at.is_(None),
)
sa.Index(
    "ix_goal_owner_deadline_active",
    Goal.user_id,
    Goal.deadline,
    Goal.id,
    postgresql_where=Goal.deleted_at.is_(None),
)

sa.Index(
    "ix_goal_owner_course_active",
    Goal.user_id,
    Goal.course_id,
    postgresql_where=Goal.deleted_at.is_(None),
)

Goal.linked_session_count = column_property(
    sa.select(sa.func.count())
    .where(
        StudySession.user_id == Goal.user_id,
        StudySession.goal_id == Goal.id,
        StudySession.deleted_at.is_(None),
    )
    .correlate_except(StudySession)
    .scalar_subquery()
)
Goal.completed_session_count = column_property(
    sa.select(sa.func.count())
    .where(
        StudySession.user_id == Goal.user_id,
        StudySession.goal_id == Goal.id,
        StudySession.deleted_at.is_(None),
        StudySession.completed.is_(True),
    )
    .correlate_except(StudySession)
    .scalar_subquery()
)


sa.Index(
    "ix_goal_owner_deleted",
    Goal.user_id,
    Goal.deleted_at,
    Goal.id,
    postgresql_where=Goal.deleted_at.is_not(None),
)
