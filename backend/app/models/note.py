from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.ownership import OwnedRecord
from app.models.soft_delete import SoftDeleteRecord


class Note(OwnedRecord, SoftDeleteRecord, Base):
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["course_id", "user_id"],
            ["course.id", "course.user_id"],
            name="fk_note_course_owner",
            ondelete="RESTRICT",
        ),
    )
    course_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sa.text("1"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


sa.Index(
    "uq_note_owner_active_key",
    Note.user_id,
    sa.func.lower(sa.func.btrim(Note.title)),
    unique=True,
    postgresql_where=Note.deleted_at.is_(None),
)
sa.Index(
    "ix_note_owner_active_position",
    Note.user_id,
    Note.position,
    Note.id,
    postgresql_where=Note.deleted_at.is_(None),
)
sa.Index(
    "ix_note_owner_updated_active",
    Note.user_id,
    Note.updated_at,
    Note.id,
    postgresql_where=Note.deleted_at.is_(None),
)
sa.Index(
    "ix_note_owner_course_active",
    Note.user_id,
    Note.course_id,
    postgresql_where=Note.deleted_at.is_(None),
)


sa.Index(
    "ix_note_owner_deleted",
    Note.user_id,
    Note.deleted_at,
    Note.id,
    postgresql_where=Note.deleted_at.is_not(None),
)
