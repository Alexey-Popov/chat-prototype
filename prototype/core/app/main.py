"""Main FastAPI application"""
import logging
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import settings
from app.core.middleware import RequestLoggingMiddleware

logger = logging.getLogger(__name__)
_CORE_ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Apply DB migrations before serving (build-time migrate often has no DB)."""
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(_CORE_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("alembic upgrade failed: %s", result.stderr or result.stdout)
        raise RuntimeError("Database migrations failed; see logs above.")
    yield


app = FastAPI(
    title="Chat System Core",
    description="FastAPI service with OAuth2, access control, and RAG",
    version="0.1.0",
    lifespan=lifespan,
)

_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
