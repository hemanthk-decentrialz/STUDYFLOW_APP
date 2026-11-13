"""Add planner dates without assigning dates to existing study sessions."""
import sqlalchemy as sa

from alembic import context, op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | None = None
depends_on: str | None = None

def upgrade() -> None:
    op.add_column("study_session", sa.Column("scheduled_date", sa.Date(), nullable=True))
    op.drop_index("uq_study_session_owner_active_key", table_name="study_session")
    op.create_index(
        "uq_study_session_owner_active_key",
        "study_session",
        ["user_id", sa.text("lower(btrim(subject))"), sa.text("lower(btrim(time))")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND scheduled_date IS NULL"),
    )
    op.create_index(
        "uq_study_session_owner_dated_key",
        "study_session",
        [
            "user_id",
            "scheduled_date",
            sa.text("lower(btrim(subject))"),
            sa.text("lower(btrim(time))"),
        ],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND scheduled_date IS NOT NULL"),
    )
    op.create_index(
        "ix_study_session_owner_date_active",
        "study_session",
        ["user_id", "scheduled_date", "time", "id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

def downgrade() -> None:
    if not context.is_offline_mode():
        duplicate = (
            op.get_bind()
            .execute(
                sa.text(
                    "SELECT 1 FROM study_session WHERE deleted_at IS NULL "
                    "GROUP BY user_id, lower(btrim(subject)), lower(btrim(time)) "
                    "HAVING count(*) > 1 LIMIT 1"
                )
            )
            .scalar()
        )
        if duplicate:
            raise RuntimeError(
                "Cannot downgrade 0008 while dated sessions repeat a subject/time. "
                "Resolve those records first; no data was deleted."
            )
    op.drop_index("ix_study_session_owner_date_active", table_name="study_session")
    op.drop_index("uq_study_session_owner_dated_key", table_name="study_session")
    op.drop_index("uq_study_session_owner_active_key", table_name="study_session")
    op.create_index(
        "uq_study_session_owner_active_key",
        "study_session",
        ["user_id", sa.text("lower(btrim(subject))"), sa.text("lower(btrim(time))")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_column("study_session", "scheduled_date")
