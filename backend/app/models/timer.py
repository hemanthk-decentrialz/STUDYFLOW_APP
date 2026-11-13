from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.ownership import OwnedRecord


class Timer(OwnedRecord, Base):
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["course_id", "user_id"],
            ["course.id", "course.user_id"],
            name="fk_timer_course_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["active_focus_id", "user_id"],
            ["focus_session.id", "focus_session.user_id"],
            name="fk_timer_focus_owner",
            ondelete="RESTRICT",
        ),
    )
    course_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    active_focus_id: Mapped[UUID | None] = mapped_column(sa.Uuid, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sa.text("0"))
    block_duration: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=sa.text("1500")
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    time_left: Mapped[int] = mapped_column(Integer, nullable=False)
    is_running: Mapped[bool] = mapped_column(Boolean, nullable=False)
    completed_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    end_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_completed_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_completed_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
