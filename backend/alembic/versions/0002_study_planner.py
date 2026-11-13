"""Initial study planner schema.
Fresh database baseline; subsequent applied revisions must remain immutable.
"""
import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None

def upgrade() -> None:
    op.create_table(
        "study_session",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("time", sa.String(length=5), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), server_default=sa.text("60"), nullable=False),
        sa.Column(
            "priority", sa.String(length=6), server_default=sa.text("'Medium'"), nullable=False
        ),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_study_session_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", "user_id", name=op.f("pk_study_session")),
    )
    op.create_index(
        "ix_study_session_owner_active_position",
        "study_session",
        ["user_id", "position", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_study_session_owner_time_active",
        "study_session",
        ["user_id", "time", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_study_session_owner_active_key",
        "study_session",
        [
            "user_id",
            sa.literal_column("lower(btrim(subject))"),
            sa.literal_column("lower(btrim(time))"),
        ],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

def downgrade() -> None:
    op.drop_index(
        "uq_study_session_owner_active_key",
        table_name="study_session",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_study_session_owner_time_active",
        table_name="study_session",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_study_session_owner_active_position",
        table_name="study_session",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("study_session")
