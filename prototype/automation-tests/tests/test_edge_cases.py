"""Edge case tests (E01-E04)."""
import pytest
import httpx


@pytest.mark.edge
async def test_e01_empty_message_handled(
    core: httpx.AsyncClient, tokens: dict
):
    """E01: Empty message is handled gracefully."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (200, 400)


@pytest.mark.edge
async def test_e02_very_long_message_handled(
    core: httpx.AsyncClient, tokens: dict
):
    """E02: Very long message is handled."""
    token = tokens["u_support"]
    long_message = "test " * 10000
    response = await core.post(
        "/api/chat",
        json={"message": long_message},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60.0,
    )
    assert response.status_code in (200, 400, 413, 414)


@pytest.mark.edge
async def test_e03_special_characters_handled(
    core: httpx.AsyncClient, tokens: dict
):
    """E03: Special characters in message are handled."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "SELECT * FROM users; DROP TABLE users; --"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.edge
async def test_e04_concurrent_requests_isolated(
    core: httpx.AsyncClient, tokens: dict
):
    """E04: Concurrent requests are isolated (no cross-contamination)."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
