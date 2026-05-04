"""Unit tests for AccessGuardrail — uses mocked DB to avoid PostgreSQL-specific SQL."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.rag.guardrail import AccessGuardrail


def _make_mock_db(rows: list[tuple]):
    """Return a mock AsyncSession whose execute() returns the given rows."""
    mock_result = MagicMock()
    mock_result.all.return_value = rows

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


async def test_guardrail_passes_when_all_chunks_allowed():
    """Guardrail passes when every chunk's table_name is in allowed patterns."""
    chunk_id = str(uuid4())
    mock_db = _make_mock_db([(chunk_id, "tickets")])

    result = await AccessGuardrail.verify(
        chunk_ids=[chunk_id],
        allowed_table_patterns={"tickets", "companies"},
        vector_db=mock_db,
    )

    assert result.passed is True
    assert result.violated_chunk_ids == []


async def test_guardrail_blocks_when_chunk_not_in_allowed():
    """Guardrail blocks when a chunk's table_name is not in allowed patterns."""
    chunk_id = str(uuid4())
    mock_db = _make_mock_db([(chunk_id, "transactions")])

    result = await AccessGuardrail.verify(
        chunk_ids=[chunk_id],
        allowed_table_patterns={"tickets"},  # transactions not allowed
        vector_db=mock_db,
    )

    assert result.passed is False
    assert chunk_id in result.violated_chunk_ids


async def test_guardrail_blocks_missing_chunk():
    """Guardrail treats a chunk not found in DB as a violation (fail-secure)."""
    chunk_id = str(uuid4())
    mock_db = _make_mock_db([])  # DB returns nothing for this chunk

    result = await AccessGuardrail.verify(
        chunk_ids=[chunk_id],
        allowed_table_patterns={"tickets"},
        vector_db=mock_db,
    )

    assert result.passed is False
    assert chunk_id in result.violated_chunk_ids


async def test_guardrail_passes_empty_chunk_list():
    """No chunks → guardrail passes (nothing to verify)."""
    mock_db = _make_mock_db([])

    result = await AccessGuardrail.verify(
        chunk_ids=[],
        allowed_table_patterns={"tickets"},
        vector_db=mock_db,
    )

    assert result.passed is True
    assert result.violated_chunk_ids == []


async def test_guardrail_mixed_allowed_and_denied():
    """Only the violated chunks are reported."""
    ok_id = str(uuid4())
    bad_id = str(uuid4())
    mock_db = _make_mock_db([(ok_id, "tickets"), (bad_id, "transactions")])

    result = await AccessGuardrail.verify(
        chunk_ids=[ok_id, bad_id],
        allowed_table_patterns={"tickets"},
        vector_db=mock_db,
    )

    assert result.passed is False
    assert bad_id in result.violated_chunk_ids
    assert ok_id not in result.violated_chunk_ids
