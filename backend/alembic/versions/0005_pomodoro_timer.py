"""Initial pomodoro timer schema.
Fresh database baseline; subsequent applied revisions must remain immutable.
"""
import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None

def upgrade() -> None:
    op.create_table(
        "timer",
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("time_left", sa.Integer(), nullable=False),
        sa.Column("is_running", sa.Boolean(), nullable=False),
        sa.Column("completed_sessions", sa.Integer(), nullable=False),
        sa.Column("end_at", sa.BigInteger(), nullable=True),
        sa.Column("last_completed_at", sa.BigInteger(), nullable=True),
        sa.Column("last_completed_mode", sa.String(length=20), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_timer_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_timer")),
    )

def downgrade() -> None:
    op.drop_table("timer")
