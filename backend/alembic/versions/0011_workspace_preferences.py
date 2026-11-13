"""Persist workspace preferences, configurable focus bounds and indexed trash reads."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "settings",
        sa.Column(
            "preferences", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )
    op.add_column(
        "timer", sa.Column("block_duration", sa.Integer(), nullable=False, server_default="1500")
    )
    op.execute(
        sa.text(
            "UPDATE timer SET block_duration = CASE mode "
            "WHEN 'Short Break' THEN 300 WHEN 'Long Break' THEN 900 ELSE 1500 END"
        )
    )
    op.drop_constraint(op.f("ck_focus_session_bounded_interval"), "focus_session", type_="check")
    op.create_check_constraint(
        op.f("ck_focus_session_bounded_interval"),
        "focus_session",
        "planned_end_at <= started_at + interval '120 minutes'",
    )
    for table in ("course", "note", "goal", "study_session"):
        op.create_index(
            f"ix_{table}_owner_deleted",
            table,
            ["user_id", "deleted_at", "id"],
            postgresql_where=sa.text("deleted_at IS NOT NULL"),
        )


def downgrade() -> None:
    # Refuse a lossy downgrade when longer recorded focus intervals exist.
    connection = op.get_bind()
    if connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM focus_session "
            "WHERE planned_end_at > started_at + interval '25 minutes')"
        )
    ):
        raise RuntimeError("Long focus intervals exist; preserve/export them before downgrading.")
    for table in ("course", "note", "goal", "study_session"):
        op.drop_index(f"ix_{table}_owner_deleted", table_name=table)
    op.drop_constraint(op.f("ck_focus_session_bounded_interval"), "focus_session", type_="check")
    op.create_check_constraint(
        op.f("ck_focus_session_bounded_interval"),
        "focus_session",
        "planned_end_at <= started_at + interval '25 minutes'",
    )
    op.drop_column("timer", "block_duration")
    op.drop_column("settings", "preferences")
