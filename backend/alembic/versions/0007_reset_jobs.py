"""Initial reset jobs schema.
Fresh database baseline; subsequent applied revisions must remain immutable.
"""
import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | None = None
depends_on: str | None = None

def upgrade() -> None:
    op.create_table(
        "job",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column(
            "status", sa.String(length=12), server_default=sa.text("'queued'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_job_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job")),
    )
    op.create_index("ix_job_owner_created", "job", ["user_id", "created_at"], unique=False)
    op.create_index(
        "ix_job_queued",
        "job",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'queued'"),
    )

def downgrade() -> None:
    op.drop_index("ix_job_queued", table_name="job", postgresql_where=sa.text("status = 'queued'"))
    op.drop_index("ix_job_owner_created", table_name="job")
    op.drop_table("job")
