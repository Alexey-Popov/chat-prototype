"""Integration tests for the ingestion pipeline."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.connectors.postgresql import PostgreSQLConnector
from app.embeddings.openai_client import EmbeddingService
from app.pipeline.ingestion import IngestionPipeline
from app.pipeline.tagger import ChunkTagger


@pytest.fixture
def test_policies_file():
    """Create a temporary policies file for testing."""
    policies_content = """
tables:
  test_table:
    allowed_roles: [SUPPORT]
    allowed_users: []
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        f.write(policies_content)
        f.flush()
        yield f.name

    Path(f.name).unlink()


@pytest.mark.asyncio
async def test_pipeline_serialize_row():
    """Test that connector serializes rows correctly."""
    connector = PostgreSQLConnector()

    row = {
        "id": "row-1",
        "title": "Test Title",
        "status": "active",
    }

    serialized = connector.serialize_row("test_table", row)

    assert "table: test_table" in serialized
    assert "id: row-1" in serialized
    assert "title: Test Title" in serialized
    assert "status: active" in serialized


@pytest.mark.asyncio
async def test_tagger_integration(test_policies_file):
    """Test tagger integration with policies."""
    tagger = ChunkTagger(test_policies_file)
    schema_hash = ChunkTagger.compute_schema_hash(["id", "title", "status"])

    metadata = tagger.get_metadata("test_table", "row-1", schema_hash)

    assert metadata["table_name"] == "test_table"
    assert metadata["allowed_roles"] == ["SUPPORT"]
    assert "schema_hash" in metadata


@pytest.mark.asyncio
async def test_embedding_service_mock():
    """Test embedding service with mock OpenAI client."""
    with patch("app.embeddings.openai_client.AsyncOpenAI"):
        service = EmbeddingService()

        # Mock the embedding response
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
        ]

        service.client.embeddings.create = AsyncMock(return_value=mock_response)

        texts = ["text 1", "text 2"]
        embeddings = await service.embed_texts(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 1536
        assert embeddings[0][0] == 0.1
        assert embeddings[1][0] == 0.2


def test_pipeline_initialization(test_policies_file):
    """Test pipeline initialization."""
    connector = PostgreSQLConnector()
    embedding_service = AsyncMock(spec=EmbeddingService)
    tagger = ChunkTagger(test_policies_file)
    source_engine = AsyncMock()
    vector_engine = AsyncMock()

    pipeline = IngestionPipeline(
        connector=connector,
        embedding_service=embedding_service,
        tagger=tagger,
        source_engine=source_engine,
        vector_engine=vector_engine,
    )

    assert pipeline.connector == connector
    assert pipeline.embedding_service == embedding_service
    assert pipeline.tagger == tagger
