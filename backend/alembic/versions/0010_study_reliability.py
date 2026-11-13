"""One coordinated update for note concurrency and server-timed focus history.
Restore reuses existing deleted_at columns and needs no schema addition.
"""
import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | None = None
depends_on: str | None = None

def upgrade() -> None:
    op.add_column("note", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.create_table(
        "focus_session",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.BigInteger(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(12), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('running', 'paused', 'completed', 'cancelled')",
            name=op.f("ck_focus_session_valid_outcome"),
        ),
        sa.CheckConstraint(
            "planned_end_at <= started_at + interval '25 minutes'",
            name=op.f("ck_focus_session_bounded_interval"),
        ),
        sa.PrimaryKeyConstraint("id", "user_id", name="pk_focus_session"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_focus_session_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "user_id"],
            ["course.id", "course.user_id"],
            name="fk_focus_session_course_owner",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at", name=op.f("ck_focus_session_valid_end")
        ),
        sa.CheckConstraint("planned_end_at > started_at", name=op.f("ck_focus_session_valid_plan")),
    )
    op.create_index(
        "ix_focus_session_owner_started", "focus_session", ["user_id", "started_at", "id"]
    )
    op.create_index(
        "ix_focus_session_owner_course_started",
        "focus_session",
        ["user_id", "course_id", "started_at"],
    )
    op.add_column("timer", sa.Column("course_id", sa.BigInteger(), nullable=True))
    op.add_column("timer", sa.Column("active_focus_id", sa.Uuid(), nullable=True))
    op.add_column("timer", sa.Column("revision", sa.Integer(), server_default="0", nullable=False))
    op.create_foreign_key(
        "fk_timer_course_owner",
        "timer",
        "course",
        ["course_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_timer_focus_owner",
        "timer",
        "focus_session",
        ["active_focus_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
    )

def downgrade() -> None:
    op.drop_constraint("fk_timer_focus_owner", "timer", type_="foreignkey")
    op.drop_constraint("fk_timer_course_owner", "timer", type_="foreignkey")
    op.drop_column("timer", "revision")
    op.drop_column("timer", "active_focus_id")
    op.drop_column("timer", "course_id")
    op.drop_index("ix_focus_session_owner_course_started", table_name="focus_session")
    op.drop_index("ix_focus_session_owner_started", table_name="focus_session")
    op.drop_table("focus_session")
    op.drop_column("note", "version")
