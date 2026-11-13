"""Initial notes schema.
Fresh database baseline; subsequent applied revisions must remain immutable.
"""
import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None

def upgrade() -> None:
    op.create_table(
        "note",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
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
            ["user_id"], ["users.id"], name=op.f("fk_note_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", "user_id", name=op.f("pk_note")),
    )
    op.create_index(
        "ix_note_owner_active_position",
        "note",
        ["user_id", "position", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_note_owner_updated_active",
        "note",
        ["user_id", "updated_at", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_note_owner_active_key",
        "note",
        ["user_id", sa.literal_column("lower(btrim(title))")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

def downgrade() -> None:
    op.drop_index(
        "uq_note_owner_active_key",
        table_name="note",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_note_owner_updated_active",
        table_name="note",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_note_owner_active_position",
        table_name="note",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("note")
