"""Request logging middleware"""
import time
from typing import Optional
from uuid import UUID
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import RequestLog
from app.db import SystemSessionLocal


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs all requests to request_log table"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        user_id: Optional[UUID] = None

        # Try to extract user_id from token if present
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                from app.core.jwt import verify_jwt_token

                token = auth_header[7:]
                token_data = verify_jwt_token(token)
                user_id = UUID(token_data.sub)
        except Exception:
            pass

        response = await call_next(request)

        latency_ms = int((time.time() - start_time) * 1000)
        endpoint = request.url.path
        method = request.method

        # Log the request asynchronously
        try:
            async with SystemSessionLocal() as db:
                log_entry = RequestLog(
                    user_id=user_id,
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                )
                db.add(log_entry)
                await db.commit()
        except Exception:
            # Silently fail logging - don't block request
            pass

        return response
