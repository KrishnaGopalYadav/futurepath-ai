"""R1 user confirmation and embedding foundation

Revision ID: 0002_r1_profile_confirmation_embeddings
Revises: 0001_initial_schema
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_r1_profile_confirmation_embeddings"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    # R1 uses pgvector as the durable embedding foundation. The actual
    # embedding is optional until an OpenAI key is configured.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column("career_profiles", sa.Column("is_user_confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("career_profiles", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))

    for table in ("experiences", "education", "projects", "certifications", "user_skills"):
        op.add_column(table, sa.Column("is_user_confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    op.create_table(
        "career_profile_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding_model", sa.String(120), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_career_profile_embeddings_user_id"),
        sa.CheckConstraint("status IN ('pending','ready','failed')", name="ck_career_profile_embeddings_status"),
    )
    op.create_index("ix_career_profile_embeddings_hash", "career_profile_embeddings", ["content_hash"])


def downgrade():
    op.drop_index("ix_career_profile_embeddings_hash", table_name="career_profile_embeddings")
    op.drop_table("career_profile_embeddings")
    for table in ("user_skills", "certifications", "projects", "education", "experiences"):
        op.drop_column(table, "is_user_confirmed")
    op.drop_column("career_profiles", "confirmed_at")
    op.drop_column("career_profiles", "is_user_confirmed")
    op.execute("DROP EXTENSION IF EXISTS vector")
