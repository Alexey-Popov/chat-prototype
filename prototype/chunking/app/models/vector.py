"""SQLAlchemy ORM models for the vector database."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import Uuid

# pgvector is only available when running against PostgreSQL.
# For unit tests (SQLite) we fall back to generic JSON columns.
try:
    from pgvector.sqlalchemy import Vector as _Vector

    VECTOR_TYPE = _Vector(1536)
    METADATA_TYPE = JSONB
except Exception:  # pragma: no cover
    VECTOR_TYPE = JSON  # type: ignore[assignment]
    METADATA_TYPE = JSON

Base = declarative_base()


class Chunk(Base):
    """Embedding chunk stored in vector database."""

    __tablename__ = "chunks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    embedding = Column(VECTOR_TYPE, nullable=True)
    # "metadata" is reserved in SQLAlchemy Declarative API — use chunk_metadata
    # but keep the underlying DB column name as "metadata" for compatibility.
    chunk_metadata = Column("metadata", METADATA_TYPE, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # PostgreSQL-specific indexes are defined conditionally so create_all
    # doesn't blow up on SQLite during unit tests.
    __table_args__ = (
        Index("idx_chunks_metadata_gin", "metadata",
              postgresql_using="gin"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.chunk_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
