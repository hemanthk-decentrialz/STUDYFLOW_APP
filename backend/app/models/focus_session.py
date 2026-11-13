from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.ownership import OwnedRecord


class FocusSession(OwnedRecord, Base):
    """One server-timed continuous interval; pausing ends the interval."""

    __table_args__ = (
        sa.CheckConstraint(
            "planned_end_at <= started_at + interval '120 minutes'", name="bounded_interval"
        ),
        sa.CheckConstraint(
            "outcome IN ('running', 'paused', 'completed', 'cancelled')", name="valid_outcome"
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "user_id"],
            ["course.id", "course.user_id"],
            name="fk_focus_session_course_owner",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="valid_end"),
        sa.CheckConstraint("planned_end_at > started_at", name="valid_plan"),
    )
    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    course_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    planned_end_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    outcome: Mapped[str] = mapped_column(sa.String(12), nullable=False, default="running")


sa.Index(
    "ix_focus_session_owner_started", FocusSession.user_id, FocusSession.started_at, FocusSession.id
)
sa.Index(
    "ix_focus_session_owner_course_started",
    FocusSession.user_id,
    FocusSession.course_id,
    FocusSession.started_at,
)
