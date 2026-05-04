"""Chat API — SSE streaming with access-controlled RAG.

Design constraints enforced here:
- P1: Access filter applied in retriever WHERE clause (not post-filter)
- P4: Policy resolved fresh from system_db per request
- P5: Any failure → error response, nothing written to chat_messages
- P6: Stateless turns — no prior messages sent to LLM
- P8: Chunk metadata stripped before LLM context
- Guardrail: runs BEFORE response is streamed; blocks and logs on violation
"""
import json
from uuid import UUID, uuid4
from typing import Optional, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.config import settings
from app.core.deps import get_current_user
from app.db import get_system_db, get_vector_db
from app.models.system import User, ChatSession, ChatMessage, RequestLog
from app.access.policy_engine import PolicyEngine
from app.rag.retriever import AccessFilteredRetriever
from app.rag.serializer import ChunkSerializer
from app.rag.guardrail import AccessGuardrail

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

router = APIRouter()

SYSTEM_PROMPT = (
    "You are an internal company assistant. "
    "Answer based only on the provided context. "
    "Do not reveal table names, database structure, chunk IDs, access policies, "
    "or information about what other users can see. "
    "If you don't have relevant information, say so clearly."
)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


async def _get_or_create_session(
    session_id: Optional[str], user_id: UUID, db: AsyncSession
) -> ChatSession:
    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == UUID(session_id),
                ChatSession.user_id == user_id,
            )
        )
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    session = ChatSession(id=uuid4(), user_id=user_id)
    db.add(session)
    await db.flush()
    return session


async def _stream_tokens(text: str) -> AsyncIterator[str]:
    """Yield pre-collected response as SSE tokens (after guardrail passed)."""
    chunk_size = 20
    for i in range(0, len(text), chunk_size):
        yield f"data: {json.dumps({'token': text[i:i+chunk_size]})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


@router.post("")
async def chat(
    req: ChatRequest,
    request: Request,
    current_user: tuple = Depends(get_current_user),
    system_db: AsyncSession = Depends(get_system_db),
    vector_db: AsyncSession = Depends(get_vector_db),
):
    user: User = current_user[0]
    user_id: UUID = user.id

    # P4: resolve policy fresh from DB every request
    allowed_patterns = await PolicyEngine.resolve(user_id, system_db)

    # P5: fail secure — get/create session (404 is a user error, not a system failure)
    session = await _get_or_create_session(req.session_id, user_id, system_db)

    # P1: access-filtered retrieval using allowed table patterns
    retriever = AccessFilteredRetriever(vector_db, allowed_patterns)
    try:
        chunks = await retriever.retrieve(req.message, top_k=5)
    except Exception:
        raise HTTPException(status_code=503, detail="Retrieval service unavailable")

    # P8: strip metadata — LLM sees plain text only
    context = ChunkSerializer.to_context(chunks)
    chunk_ids = [c.chunk_id for c in chunks]

    # P6: stateless — only system prompt + context + current message
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ])

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
        streaming=False,  # collect full response before guardrail
    )

    try:
        chain = prompt | llm
        response = await chain.ainvoke({"context": context, "question": req.message})
        full_response: str = response.content
    except Exception:
        raise HTTPException(status_code=504, detail="LLM unavailable")

    # Guardrail: re-verify chunks BEFORE streaming response (P5: fail secure)
    try:
        guardrail = await AccessGuardrail.verify(chunk_ids, allowed_patterns, vector_db)
    except Exception:
        # Guardrail failure = treat as BLOCK (P5)
        raise HTTPException(status_code=403, detail="Access verification failed")

    if not guardrail.passed:
        # Log violation to request_log with HIGH severity
        await system_db.execute(
            text("""
                UPDATE request_log SET violation_chunk_ids = :vids, severity = 'HIGH'
                WHERE id = (SELECT id FROM request_log WHERE user_id = :uid
                            ORDER BY created_at DESC LIMIT 1)
            """),
            {"vids": json.dumps(guardrail.violated_chunk_ids), "uid": str(user_id)},
        )
        await system_db.commit()
        raise HTTPException(status_code=403, detail="Access denied")

    # Guardrail passed — persist user message + assistant response
    system_db.add(ChatMessage(
        id=uuid4(), session_id=session.id, user_id=user_id,
        role="user", content=req.message, chunk_ids=json.dumps(chunk_ids),
        guardrail_result="PASS",
    ))
    system_db.add(ChatMessage(
        id=uuid4(), session_id=session.id, user_id=user_id,
        role="assistant", content=full_response, chunk_ids=json.dumps(chunk_ids),
        guardrail_result="PASS",
    ))
    await system_db.commit()

    # Stream pre-collected response as SSE
    return StreamingResponse(_stream_tokens(full_response), media_type="text/event-stream")


@router.get("/history")
async def chat_history(
    current_user: tuple = Depends(get_current_user),
    system_db: AsyncSession = Depends(get_system_db),
):
    user: User = current_user[0]
    result = await system_db.execute(
        select(ChatSession).where(ChatSession.user_id == user.id)
    )
    sessions = result.scalars().all()

    out = []
    for s in sessions:
        msgs = await system_db.execute(
            select(ChatMessage).where(ChatMessage.session_id == s.id)
            .order_by(ChatMessage.created_at)
        )
        out.append({
            "id": str(s.id),
            "created_at": s.created_at.isoformat(),
            "messages": [
                {"id": str(m.id), "role": m.role, "content": m.content,
                 "created_at": m.created_at.isoformat()}
                for m in msgs.scalars().all()
            ],
        })
    return {"sessions": out}
