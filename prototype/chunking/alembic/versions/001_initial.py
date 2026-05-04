"""Create chunks table and indexes.

Revision ID: 001
Revises:
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""
    # Enable vector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Create chunks table
    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(dim=1536), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "idx_chunks_embedding",
        "chunks",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_index(
        "idx_chunks_metadata",
        "chunks",
        ["metadata"],
        postgresql_using="gin",
    )

    op.create_index(
        "idx_chunks_table_row",
        "chunks",
        [sa.text("(metadata->>'table_name')"), sa.text("(metadata->>'row_id')")],
    )


def downgrade() -> None:
    """Drop initial schema."""
    op.drop_table("chunks")
