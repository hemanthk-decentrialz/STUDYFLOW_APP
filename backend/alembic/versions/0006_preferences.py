"""Initial preferences schema.
Fresh database baseline; subsequent applied revisions must remain immutable.
"""
import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | None = None
depends_on: str | None = None

def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("theme", sa.String(length=5), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_settings_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_settings")),
    )

def downgrade() -> None:
    op.drop_table("settings")
