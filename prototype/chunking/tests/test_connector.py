"""Tests for data connectors."""

import pytest
from app.connectors.postgresql import PostgreSQLConnector


def test_connector_serialize_row():
    """Test row serialization."""
    connector = PostgreSQLConnector()

    row = {
        "id": "12345",
        "name": "Test User",
        "email": "test@example.com",
        "created_at": "2026-01-01T00:00:00",
    }

    serialized = connector.serialize_row("users", row)

    assert "table: users" in serialized
    assert "id: 12345" in serialized
    assert "name: Test User" in serialized
    assert "email: test@example.com" in serialized
    assert "created_at: 2026-01-01T00:00:00" in serialized
    assert " | " in serialized


def test_connector_serialize_row_with_none():
    """Test row serialization with None values."""
    connector = PostgreSQLConnector()

    row = {
        "id": "12345",
        "name": "Test",
        "description": None,
    }

    serialized = connector.serialize_row("items", row)

    assert "table: items" in serialized
    assert "description: null" in serialized


def test_connector_serialize_row_with_uuid():
    """Test row serialization with UUID objects."""
    from uuid import UUID

    connector = PostgreSQLConnector()

    test_uuid = UUID("550e8400-e29b-41d4-a716-446655440000")
    row = {
        "id": test_uuid,
        "name": "Test",
    }

    serialized = connector.serialize_row("records", row)

    assert "table: records" in serialized
    assert "550e8400-e29b-41d4-a716-446655440000" in serialized
