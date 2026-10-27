"""Reconcile R1 schema additions for databases stamped at 0002.

Revision ID: 0003_r1_schema_reconciliation
Revises: 0002_r1_profile_confirmation_embeddings
Create Date: 2026-10-27

Some development databases were able to reach the 0002 Alembic revision while
still missing one or more R1 schema objects. This migration is deliberately
idempotent: it reconciles the expected R1 schema without requiring manual SQL
or a database reset.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_r1_schema_reconciliation"
down_revision = "0002_r1_profile_confirmation_embeddings"
branch_labels = None
depends_on = None


R1_CONFIRMATION_COLUMNS = (
    ("career_profiles", "is_user_confirmed", sa.Boolean(), sa.text("false")),
    ("career_profiles", "confirmed_at", sa.DateTime(timezone=True), None),
    ("experiences", "is_user_confirmed", sa.Boolean(), sa.text("false")),
    ("education", "is_user_confirmed", sa.Boolean(), sa.text("false")),
    ("projects", "is_user_confirmed", sa.Boolean(), sa.text("false")),
    ("certifications", "is_user_confirmed", sa.Boolean(), sa.text("false")),
    ("user_skills", "is_user_confirmed", sa.Boolean(), sa.text("false")),
)


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _has_column(bind, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in sa.inspect(bind).get_columns(table_name))


def upgrade():
    bind = op.get_bind()

    # Reconcile confirmation fields independently so a partially-applied R1
    # schema can be repaired safely. The defaults make existing rows valid.
    for table_name, column_name, column_type, server_default in R1_CONFIRMATION_COLUMNS:
        if not _has_table(bind, table_name):
            raise RuntimeError(
                f"R1 schema reconciliation expected table {table_name!r}, but it does not exist"
            )
        if not _has_column(bind, table_name, column_name):
            kwargs = {
                "nullable": column_name != "is_user_confirmed",
            }
            if server_default is not None:
                kwargs["server_default"] = server_default
            op.add_column(table_name, sa.Column(column_name, column_type, **kwargs))

    # Reconcile the embedding foundation as well. This keeps databases that
    # were stamped at 0002 but missed the table usable by the R1 API.
    if not _has_table(bind, "career_profile_embeddings"):
        op.create_table(
            "career_profile_embeddings",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("embedding_model", sa.String(120), nullable=False),
            sa.Column("dimensions", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), server_default="pending", nullable=False),
            sa.Column("embedding", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("user_id", name="uq_career_profile_embeddings_user_id"),
            sa.CheckConstraint(
                "status IN ('pending','ready','failed')",
                name="ck_career_profile_embeddings_status",
            ),
        )

    inspector = sa.inspect(bind)
    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes("career_profile_embeddings")
    }
    if "ix_career_profile_embeddings_hash" not in existing_indexes:
        op.create_index(
            "ix_career_profile_embeddings_hash",
            "career_profile_embeddings",
            ["content_hash"],
        )


def downgrade():
    # Do not remove R1 schema objects on downgrade. The reconciliation migration
    # repairs drift introduced by an inconsistent 0002 state; removing objects
    # here could destroy valid user data. The normal 0002 downgrade remains the
    # authoritative destructive rollback.
    pass
