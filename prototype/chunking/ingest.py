"""CLI entrypoint for the chunking service ingestion."""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

import click

from app.config import settings
from app.connectors.postgresql import PostgreSQLConnector
from app.db import close_engines, init_engines
from app.embeddings.openai_client import EmbeddingService
from app.pipeline.ingestion import IngestionPipeline
from app.pipeline.tagger import ChunkTagger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--source-dsn",
    envvar="SOURCE_DSN",
    required=False,
    help="Source database DSN (env: SOURCE_DSN)",
)
@click.option(
    "--vector-dsn",
    envvar="VECTOR_DSN",
    required=False,
    help="Vector database DSN (env: VECTOR_DSN)",
)
@click.option(
    "--policy-config",
    type=click.Path(exists=True),
    default="policies.yaml",
    help="Path to policy configuration file",
)
@click.option(
    "--table",
    default=None,
    help="Specific table to ingest (default: all tables)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-indexing even if schema hash matches",
)
def main(
    source_dsn: str | None,
    vector_dsn: str | None,
    policy_config: str,
    table: str | None,
    force: bool,
) -> None:
    """Ingest data from source database to vector database."""
    # Use provided DSNs or fall back to environment/config
    if source_dsn:
        os.environ["SOURCE_DSN"] = source_dsn
    if vector_dsn:
        os.environ["VECTOR_DSN"] = vector_dsn

    # Re-load settings with new environment
    from importlib import reload
    import app.config
    reload(app.config)
    from app.config import settings as updated_settings

    logger.info(f"Source DSN: {updated_settings.source_dsn[:50]}...")
    logger.info(f"Vector DSN: {updated_settings.vector_dsn[:50]}...")
    logger.info(f"Policy config: {policy_config}")

    # Run ingestion
    asyncio.run(_run_ingestion(policy_config, table, force))


async def _run_ingestion(policy_config: str, table: str | None, force: bool) -> None:
    """Run the ingestion process."""
    try:
        # Initialize databases
        logger.info("Initializing database connections...")
        source_engine, vector_engine = await init_engines()

        # Run Alembic migrations
        logger.info("Running database migrations...")
        await _run_migrations()

        # Initialize services
        logger.info("Initializing embedding service...")
        embedding_service = EmbeddingService()

        logger.info("Loading policies...")
        tagger = ChunkTagger(policy_config)

        connector = PostgreSQLConnector()

        # Create pipeline
        pipeline = IngestionPipeline(
            connector=connector,
            embedding_service=embedding_service,
            tagger=tagger,
            source_engine=source_engine,
            vector_engine=vector_engine,
        )

        # Run ingestion
        logger.info("Starting ingestion...")
        if table:
            logger.info(f"Ingesting single table: {table}")
            result = await pipeline.ingest_table(table, force=force)
            logger.info(f"Result: {result}")
        else:
            logger.info("Ingesting all tables...")
            result = await pipeline.ingest_all(force=force)
            logger.info(f"Summary: {result}")

        # Cleanup
        await embedding_service.close()
        await close_engines()

        logger.info("Ingestion completed successfully")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


async def _run_migrations() -> None:
    """Run Alembic migrations in a subprocess.

    ``alembic.command.upgrade()`` must not be called from inside this app's asyncio
    loop: ``chunking/alembic/env.py`` uses ``asyncio.run()`` at import time, which
    conflicts with ``asyncio.run(_run_ingestion(...))`` in :func:`main`.

    Use ``settings.vector_dsn`` from the reloaded ``app.config`` (not ``str(engine.url)``)
    so the password is not masked in the subprocess environment.
    """
    from app.config import settings as cfg

    chunking_root = Path(__file__).resolve().parent
    env = os.environ.copy()
    env["VECTOR_DSN"] = cfg.vector_dsn
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(chunking_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error("alembic stdout: %s", result.stdout)
        logger.error("alembic stderr: %s", result.stderr)
        raise RuntimeError("Vector DB Alembic migrations failed")


if __name__ == "__main__":
    main()
