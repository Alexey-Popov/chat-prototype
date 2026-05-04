"""FastAPI application for the chunking service."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.connectors.postgresql import PostgreSQLConnector
from app.db import close_engines, init_engines
from app.embeddings.openai_client import EmbeddingService
from app.pipeline.ingestion import IngestionPipeline
from app.pipeline.tagger import ChunkTagger

logger = logging.getLogger(__name__)

# Global state
embedding_service: EmbeddingService | None = None
pipeline: IngestionPipeline | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str


class IngestRequest(BaseModel):
    """Request to trigger ingestion."""

    table: str | None = None
    force: bool = False


class IngestResponse(BaseModel):
    """Response from ingestion request."""

    status: str
    summary: dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global embedding_service, pipeline

    logger.info("Starting chunking service")

    # Initialize database engines
    source_engine, vector_engine = await init_engines()

    # Initialize embedding service
    embedding_service = EmbeddingService()

    # Load policies
    tagger = ChunkTagger("policies.yaml")

    # Initialize connector
    connector = PostgreSQLConnector()

    # Initialize pipeline
    pipeline = IngestionPipeline(
        connector=connector,
        embedding_service=embedding_service,
        tagger=tagger,
        source_engine=source_engine,
        vector_engine=vector_engine,
    )

    logger.info("Chunking service initialized")

    yield

    logger.info("Shutting down chunking service")

    # Cleanup
    if embedding_service:
        await embedding_service.close()

    await close_engines()


app = FastAPI(title="Chunking Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.post("/api/ingest", response_model=IngestResponse)
async def trigger_ingest(request: IngestRequest) -> IngestResponse:
    """Trigger data ingestion."""
    if pipeline is None:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")

    try:
        if request.table:
            result = await pipeline.ingest_table(request.table, force=request.force)
            summary = {"tables": [result]}
        else:
            result = await pipeline.ingest_all(force=request.force)
            summary = result

        return IngestResponse(status="success", summary=summary)

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
