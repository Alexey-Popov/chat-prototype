"""Audit log API endpoints."""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.deps import get_admin_user
from app.models.system import User, RequestLog, ChatMessage

router = APIRouter(prefix="/api/admin/audit", tags=["audit"])


# ============================================================================
# Pydantic Models
# ============================================================================


class RequestLogResponse(BaseModel):
    """Request log response."""

    id: UUID
    user_id: Optional[UUID]
    endpoint: str
    method: str
    status_code: int
    latency_ms: int
    violation_chunk_ids: Optional[dict]
    severity: str
    created_at: str

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    """Chat message response."""

    id: UUID
    session_id: UUID
    user_id: UUID
    role: str
    content: str
    chunk_ids: Optional[dict]
    guardrail_result: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class PaginatedRequestLogsResponse(BaseModel):
    """Paginated request logs response."""

    items: List[RequestLogResponse]
    total: int
    page: int
    size: int


class PaginatedChatMessagesResponse(BaseModel):
    """Paginated chat messages response."""

    items: List[ChatMessageResponse]
    total: int
    page: int
    size: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/requests", response_model=PaginatedRequestLogsResponse)
async def list_request_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = Query(None),
    severity: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRequestLogsResponse:
    """List request logs with optional filters and pagination."""
    offset = (page - 1) * size

    # Build query filters
    filters = []
    if user_id:
        filters.append(RequestLog.user_id == user_id)
    if severity:
        filters.append(RequestLog.severity == severity)
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            filters.append(RequestLog.created_at >= start)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format (use ISO 8601)",
            )
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            filters.append(RequestLog.created_at <= end)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format (use ISO 8601)",
            )

    # Count total
    query = select(func.count(RequestLog.id))
    if filters:
        query = query.where(and_(*filters))
    result = await db.execute(query)
    total = result.scalar() or 0

    # Fetch logs
    query = select(RequestLog).order_by(desc(RequestLog.created_at))
    if filters:
        query = query.where(and_(*filters))
    query = query.offset(offset).limit(size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return PaginatedRequestLogsResponse(
        items=[
            RequestLogResponse(
                id=log.id,
                user_id=log.user_id,
                endpoint=log.endpoint,
                method=log.method,
                status_code=log.status_code,
                latency_ms=log.latency_ms,
                violation_chunk_ids=log.violation_chunk_ids,
                severity=log.severity,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ],
        total=total,
        page=page,
        size=size,
    )


@router.get("/chat", response_model=PaginatedChatMessagesResponse)
async def list_chat_messages(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = Query(None),
    session_id: Optional[UUID] = Query(None),
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedChatMessagesResponse:
    """List chat messages with optional filters and pagination."""
    offset = (page - 1) * size

    # Build query filters
    filters = []
    if user_id:
        filters.append(ChatMessage.user_id == user_id)
    if session_id:
        filters.append(ChatMessage.session_id == session_id)

    # Count total
    query = select(func.count(ChatMessage.id))
    if filters:
        query = query.where(and_(*filters))
    result = await db.execute(query)
    total = result.scalar() or 0

    # Fetch messages
    query = select(ChatMessage).order_by(desc(ChatMessage.created_at))
    if filters:
        query = query.where(and_(*filters))
    query = query.offset(offset).limit(size)
    result = await db.execute(query)
    messages = result.scalars().all()

    return PaginatedChatMessagesResponse(
        items=[
            ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                user_id=msg.user_id,
                role=msg.role,
                content=msg.content,
                chunk_ids=msg.chunk_ids,
                guardrail_result=msg.guardrail_result,
                created_at=msg.created_at.isoformat(),
            )
            for msg in messages
        ],
        total=total,
        page=page,
        size=size,
    )
