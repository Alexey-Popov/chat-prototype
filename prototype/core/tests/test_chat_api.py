"""Integration tests for chat API"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from app.models import User, Role, UserRole, ChatSession
from app.core.jwt import create_jwt_token


async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_chat_requires_auth(client: AsyncClient):
    """No token → HTTPBearer returns 403 (FastAPI security default)."""
    response = await client.post("/api/chat", json={"message": "Hello"})
    assert response.status_code == 401


async def test_chat_history_requires_auth(client: AsyncClient):
    response = await client.get("/api/chat/history")
    assert response.status_code == 401


async def test_chat_history_returns_sessions(client: AsyncClient, test_system_db):
    async with test_system_db() as db:
        user = User(id=uuid4(), oauth_sub="test_user2", email="test2@test.com", active=True)
        role = Role(id=uuid4(), name="viewer")
        db.add(user)
        db.add(role)
        await db.flush()

        db.add(UserRole(user_id=user.id, role_id=role.id))
        session = ChatSession(id=uuid4(), user_id=user.id)
        db.add(session)
        await db.commit()

        token = create_jwt_token(user.id, [role.id], user.email)
        response = await client.get(
            "/api/chat/history",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) >= 1
        ids = [s["id"] for s in data["sessions"]]
        assert str(session.id) in ids
