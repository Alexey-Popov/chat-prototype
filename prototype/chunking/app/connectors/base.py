"""Base connector interface for data ingestion."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine


class DataConnector(ABC):
    """Abstract base class for data connectors."""

    @abstractmethod
    async def get_tables(self, engine: AsyncEngine) -> list[str]:
        """Get list of table names from the source database."""
        pass

    @abstractmethod
    async def get_rows(
        self, engine: AsyncEngine, table: str
    ) -> AsyncIterator[dict[str, Any]]:
        """Iterate over rows from a table."""
        pass

    @abstractmethod
    def serialize_row(self, table: str, row: dict[str, Any]) -> str:
        """Serialize a row to a text string for embedding."""
        pass
