"""Promote existing subjects to owned courses and link study resources."""
import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | None = None
depends_on: str | None = None

def upgrade() -> None:
    op.create_table(
        "course",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", "user_id", name="pk_course"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_course_user_id_users", ondelete="CASCADE"
        ),
    )
    # Keep every resource, including deleted ones. Blank legacy subjects become General study.
    op.execute(
        sa.text("""
        WITH labels AS (
            SELECT user_id, coalesce(nullif(btrim(subject), ''), 'General study') AS title
            FROM study_session
            UNION ALL
            SELECT user_id, coalesce(nullif(btrim(subject), ''), 'General study') FROM note
            UNION ALL
            SELECT user_id, coalesce(nullif(btrim(subject), ''), 'General study') FROM goal
        ), names AS (
            SELECT user_id, lower(title) AS normalized, min(title) AS title
            FROM labels GROUP BY user_id, lower(title)
        ), numbered AS (
            SELECT user_id, title,
                   row_number() OVER (PARTITION BY user_id ORDER BY normalized) AS id
            FROM names
        )
        INSERT INTO course (id, user_id, title, description, position)
        SELECT id, user_id, title, '', id - 1 FROM numbered
    """)
    )
    op.create_index(
        "uq_course_owner_active_key",
        "course",
        ["user_id", sa.text("lower(btrim(title))")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_course_owner_active_position",
        "course",
        ["user_id", "position", "id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    for table in ("study_session", "note", "goal"):
        op.add_column(table, sa.Column("course_id", sa.BigInteger(), nullable=True))
        # Table names are fixed migration constants; values never come from requests.
        op.execute(
            sa.text(f"""
            UPDATE {table} AS resource SET course_id = course.id, subject = course.title
            FROM course WHERE course.user_id = resource.user_id
              AND lower(btrim(course.title)) =
                  lower(coalesce(nullif(btrim(resource.subject), ''), 'General study'))
        """)
        )
        op.alter_column(table, "course_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_course_owner",
            table,
            "course",
            ["course_id", "user_id"],
            ["id", "user_id"],
            ondelete="RESTRICT",
        )
        op.create_index(
            f"ix_{table}_owner_course_active",
            table,
            ["user_id", "course_id"],
            postgresql_where=sa.text("deleted_at IS NULL"),
        )
    op.create_unique_constraint("uq_goal_id_owner_course", "goal", ["id", "user_id", "course_id"])
    op.add_column("study_session", sa.Column("goal_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_study_session_goal_owner",
        "study_session",
        "goal",
        ["goal_id", "user_id", "course_id"],
        ["id", "user_id", "course_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_study_session_owner_goal_active",
        "study_session",
        ["user_id", "goal_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

def downgrade() -> None:
    # Labels remain available to the previous application; relationships are intentionally removed.
    op.drop_index("ix_study_session_owner_goal_active", table_name="study_session")
    op.drop_constraint("fk_study_session_goal_owner", "study_session", type_="foreignkey")
    op.drop_column("study_session", "goal_id")
    op.drop_constraint("uq_goal_id_owner_course", "goal", type_="unique")
    for table in ("study_session", "note", "goal"):
        op.drop_index(f"ix_{table}_owner_course_active", table_name=table)
        op.drop_constraint(f"fk_{table}_course_owner", table, type_="foreignkey")
        op.drop_column(table, "course_id")
    op.drop_index("ix_course_owner_active_position", table_name="course")
    op.drop_index("uq_course_owner_active_key", table_name="course")
    op.drop_table("course")
