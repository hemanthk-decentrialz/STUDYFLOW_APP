"""Initial goals schema.
Fresh database baseline; subsequent applied revisions must remain immutable.
"""
import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None

def upgrade() -> None:
    op.create_table(
        "goal",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_goal_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", "user_id", name=op.f("pk_goal")),
    )
    op.create_index(
        "ix_goal_owner_active_position",
        "goal",
        ["user_id", "position", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_goal_owner_deadline_active",
        "goal",
        ["user_id", "deadline", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_goal_owner_active_key",
        "goal",
        ["user_id", sa.literal_column("lower(btrim(title))")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

def downgrade() -> None:
    op.drop_index(
        "uq_goal_owner_active_key",
        table_name="goal",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_goal_owner_deadline_active",
        table_name="goal",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_goal_owner_active_position",
        table_name="goal",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("goal")
