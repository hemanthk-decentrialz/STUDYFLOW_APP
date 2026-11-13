from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.ownership import OwnedRecord
from app.models.soft_delete import SoftDeleteRecord


class Course(OwnedRecord, SoftDeleteRecord, Base):
    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    description: Mapped[str] = mapped_column(sa.String(2000), nullable=False, default="")
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


sa.Index(
    "uq_course_owner_active_key",
    Course.user_id,
    sa.func.lower(sa.func.btrim(Course.title)),
    unique=True,
    postgresql_where=Course.deleted_at.is_(None),
)
sa.Index(
    "ix_course_owner_active_position",
    Course.user_id,
    Course.position,
    Course.id,
    postgresql_where=Course.deleted_at.is_(None),
)


sa.Index(
    "ix_course_owner_deleted",
    Course.user_id,
    Course.deleted_at,
    Course.id,
    postgresql_where=Course.deleted_at.is_not(None),
)
