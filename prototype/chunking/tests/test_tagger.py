"""Tests for chunk tagging with access control."""

import pytest
import tempfile
from pathlib import Path

from app.pipeline.tagger import ChunkTagger


@pytest.fixture
def test_policies_file():
    """Create a temporary policies file for testing."""
    policies_content = """
tables:
  tickets:
    allowed_roles: [SUPPORT]
    allowed_users: []
  transactions:
    allowed_roles: [FINANCE]
    allowed_users: []
  shared_table:
    allowed_roles: [SUPPORT, FINANCE]
    allowed_users: [user1, user2]
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        f.write(policies_content)
        f.flush()
        yield f.name

    Path(f.name).unlink()


def test_tagger_get_metadata(test_policies_file):
    """Test metadata generation."""
    tagger = ChunkTagger(test_policies_file)

    metadata = tagger.get_metadata("tickets", "row-123", "hash123")

    assert metadata["table_name"] == "tickets"
    assert metadata["row_id"] == "row-123"
    assert metadata["schema_hash"] == "hash123"
    assert metadata["allowed_roles"] == ["SUPPORT"]
    assert metadata["allowed_users"] == []


def test_tagger_get_metadata_multiple_roles(test_policies_file):
    """Test metadata for table with multiple roles."""
    tagger = ChunkTagger(test_policies_file)

    metadata = tagger.get_metadata("shared_table", "row-456", "hash456")

    assert metadata["allowed_roles"] == ["SUPPORT", "FINANCE"]
    assert metadata["allowed_users"] == ["user1", "user2"]


def test_tagger_get_metadata_invalid_table(test_policies_file):
    """Test that invalid table raises error."""
    tagger = ChunkTagger(test_policies_file)

    with pytest.raises(ValueError, match="not found in policies"):
        tagger.get_metadata("nonexistent_table", "row-789", "hash789")


def test_tagger_compute_schema_hash():
    """Test schema hash computation."""
    hash1 = ChunkTagger.compute_schema_hash(["id", "name", "email"])
    hash2 = ChunkTagger.compute_schema_hash(["id", "name", "email"])
    hash3 = ChunkTagger.compute_schema_hash(["id", "name", "phone"])

    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 16


def test_tagger_compute_schema_hash_order_independent():
    """Test that column order doesn't affect hash."""
    hash1 = ChunkTagger.compute_schema_hash(["z_col", "a_col", "m_col"])
    hash2 = ChunkTagger.compute_schema_hash(["a_col", "m_col", "z_col"])

    assert hash1 == hash2
