"""Main ingestion pipeline orchestration."""

import json
import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.connectors.base import DataConnector
from app.embeddings.openai_client import EmbeddingService
from app.models.vector import Chunk
from app.pipeline.tagger import ChunkTagger

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates data ingestion from source to vector database."""

    def __init__(
        self,
        connector: DataConnector,
        embedding_service: EmbeddingService,
        tagger: ChunkTagger,
        source_engine: AsyncEngine,
        vector_engine: AsyncEngine,
    ) -> None:
        """Initialize the ingestion pipeline."""
        self.connector = connector
        self.embedding_service = embedding_service
        self.tagger = tagger
        self.source_engine = source_engine
        self.vector_engine = vector_engine

    async def ingest_table(
        self, table: str, force: bool = False
    ) -> dict[str, Any]:
        """Ingest a single table from source to vector database."""
        logger.info(f"Starting ingestion for table: {table}")

        # Get column info for schema hash
        async with self.source_engine.connect() as conn:
            columns = await conn.run_sync(
                lambda sync_conn: [c["name"] for c in inspect(sync_conn).get_columns(table)]
            )

        schema_hash = ChunkTagger.compute_schema_hash(columns)
        logger.info(f"Schema hash for {table}: {schema_hash}")

        # Fetch all rows from source
        all_rows: list[dict[str, Any]] = []
        async for row in self.connector.get_rows(self.source_engine, table):
            all_rows.append(row)

        logger.info(f"Found {len(all_rows)} rows in {table}")

        # Check if we need to re-index
        if not force:
            should_skip = await self._should_skip_table(
                table, schema_hash, len(all_rows)
            )
            if should_skip:
                logger.info(f"Skipping {table} - no schema changes or data changes")
                return {
                    "table": table,
                    "rows_processed": 0,
                    "chunks_created": 0,
                    "skipped": True,
                }

        # Serialize rows to text
        texts: list[str] = []
        row_ids: list[str] = []

        for row in all_rows:
            # Extract primary key (assume 'id' column exists)
            row_id = str(row.get("id", ""))
            text = self.connector.serialize_row(table, row)

            texts.append(text)
            row_ids.append(row_id)

        logger.info(f"Serialized {len(texts)} texts for embedding")

        # Embed texts
        embeddings = await self.embedding_service.embed_texts(texts)
        logger.info(f"Generated {len(embeddings)} embeddings")

        # Upsert chunks into vector database
        chunks_created = await self._upsert_chunks(
            table, row_ids, texts, embeddings, schema_hash
        )

        # Delete chunks for rows no longer in source
        chunks_deleted = await self._delete_stale_chunks(table, row_ids)

        logger.info(
            f"Completed ingestion for {table}: "
            f"created={chunks_created}, deleted={chunks_deleted}"
        )

        return {
            "table": table,
            "rows_processed": len(all_rows),
            "chunks_created": chunks_created,
            "chunks_deleted": chunks_deleted,
            "skipped": False,
        }

    async def ingest_all(self, force: bool = False) -> dict[str, Any]:
        """Ingest all tables from source to vector database."""
        tables = await self.connector.get_tables(self.source_engine)
        logger.info(f"Found {len(tables)} tables to ingest")

        results = {"tables": [], "total_rows": 0, "total_chunks": 0}

        for table in tables:
            try:
                result = await self.ingest_table(table, force=force)
                results["tables"].append(result)
                results["total_rows"] += result["rows_processed"]
                results["total_chunks"] += result["chunks_created"]
            except Exception as e:
                logger.error(f"Error ingesting {table}: {e}")
                results["tables"].append(
                    {"table": table, "error": str(e), "skipped": True}
                )

        return results

    async def _should_skip_table(
        self, table: str, schema_hash: str, row_count: int
    ) -> bool:
        """Check if table should be skipped (no changes detected)."""
        async with self.vector_engine.connect() as conn:
            # Query for existing chunks for this table
            result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*) as cnt, 
                           metadata->>'schema_hash' as hash
                    FROM chunks
                    WHERE metadata->>'table_name' = :table
                    GROUP BY metadata->>'schema_hash'
                    """
                ),
                {"table": table},
            )
            row = result.first()

            if row is None:
                # No chunks exist yet
                return False

            existing_count = row[0]
            existing_hash = row[1]

            # Skip if schema hash matches and row count matches
            if existing_hash == schema_hash and existing_count == row_count:
                return True

            return False

    async def _upsert_chunks(
        self,
        table: str,
        row_ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        schema_hash: str,
    ) -> int:
        """Upsert chunks into vector database."""
        created_count = 0

        async_session = async_sessionmaker(
            self.vector_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            for row_id, row_text, embedding in zip(row_ids, texts, embeddings):
                metadata = self.tagger.get_metadata(table, row_id, schema_hash)
                md = json.dumps(metadata)

                await session.execute(
                    text(
                        """
                        DELETE FROM chunks
                        WHERE metadata->>'table_name' = :table
                          AND metadata->>'row_id' = :row_id
                        """
                    ),
                    {"table": table, "row_id": row_id},
                )
                vec = "[" + ",".join(str(float(x)) for x in embedding) + "]"
                await session.execute(
                    text(
                        """
                        INSERT INTO chunks (id, content, embedding, metadata)
                        VALUES (gen_random_uuid(), :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
                        """
                    ),
                    {
                        "content": row_text,
                        "embedding": vec,
                        "metadata": md,
                    },
                )
                created_count += 1

            await session.commit()

        return created_count

    async def _delete_stale_chunks(self, table: str, current_row_ids: list[str]) -> int:
        """Delete chunks for rows no longer in source database."""
        async with self.vector_engine.connect() as conn:
            # Delete chunks where row_id is not in current_row_ids
            if current_row_ids:
                placeholders = ",".join([f"'{rid}'" for rid in current_row_ids])
                query = f"""
                    DELETE FROM chunks
                    WHERE metadata->>'table_name' = '{table}'
                    AND metadata->>'row_id' NOT IN ({placeholders})
                """
            else:
                # If no rows exist, delete all chunks for this table
                query = f"""
                    DELETE FROM chunks
                    WHERE metadata->>'table_name' = '{table}'
                """

            result = await conn.execute(text(query))
            deleted = result.rowcount

            await conn.commit()

        return deleted or 0
