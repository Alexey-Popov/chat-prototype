"""PostgreSQL connector for data ingestion."""

from typing import Any, AsyncIterator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

from .base import DataConnector


class PostgreSQLConnector(DataConnector):
    """Connector for PostgreSQL databases."""

    async def get_tables(self, engine: AsyncEngine) -> list[str]:
        """Get list of table names from the database."""

        def _table_names(sync_conn):
            return inspect(sync_conn).get_table_names()

        async with engine.connect() as conn:
            return await conn.run_sync(_table_names)

    async def get_rows(
        self, engine: AsyncEngine, table: str
    ) -> AsyncIterator[dict[str, Any]]:
        """Iterate over rows from a table."""
        async with engine.connect() as conn:
            result = await conn.execute(text(f'SELECT * FROM "{table}"'))
            rows = result.fetchall()

        for row in rows:
            # Convert Row to dict
            yield dict(row._mapping)

    def serialize_row(self, table: str, row: dict[str, Any]) -> str:
        """Serialize a row to text format: 'table: {table} | col1: val1 | col2: val2 | ...'"""
        parts = [f"table: {table}"]
        for key, value in row.items():
            # Handle None values
            if value is None:
                value_str = "null"
            # Handle UUID objects
            elif hasattr(value, "__str__") and not isinstance(value, str):
                value_str = str(value)
            else:
                value_str = str(value)

            parts.append(f"{key}: {value_str}")

        return " | ".join(parts)
