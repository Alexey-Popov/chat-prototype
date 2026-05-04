"""Authentication tests (A01-A05)."""
import pytest
import httpx


@pytest.mark.auth
async def test_a01_no_token_unauthorized(core: httpx.AsyncClient):
    """A01: Request without JWT → 401 Unauthorized."""
    response = await core.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 401


@pytest.mark.auth
async def test_a02_invalid_token_unauthorized(core: httpx.AsyncClient):
    """A02: Request with invalid JWT → 401 Unauthorized."""
    response = await core.post(
        "/api/chat",
        json={"message": "hello"},
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401


@pytest.mark.auth
async def test_a03_malformed_bearer_unauthorized(core: httpx.AsyncClient):
    """A03: Malformed Authorization header → 401 Unauthorized."""
    response = await core.post(
        "/api/chat",
        json={"message": "hello"},
        headers={"Authorization": "InvalidPrefix token"},
    )
    assert response.status_code == 401


@pytest.mark.auth
async def test_a04_expired_token_unauthorized(core: httpx.AsyncClient):
    """A04: Request with expired JWT → 401 Unauthorized."""
    response = await core.post(
        "/api/chat",
        json={"message": "hello"},
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjB9.invalid"},
    )
    assert response.status_code == 401


@pytest.mark.auth
async def test_a05_dev_login_creates_user(core: httpx.AsyncClient):
    """A05: DEV_MOCK_USER login creates user and returns JWT."""
    email = "newdev@test.com"
    response = await core.get(
        "/auth/dev-login",
        params={"email": email},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0
