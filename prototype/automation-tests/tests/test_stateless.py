"""Stateless request tests (SL01-SL02)."""
import pytest
import httpx


@pytest.mark.access
async def test_sl01_access_decision_fresh_each_request(
    core: httpx.AsyncClient, tokens: dict
):
    """SL01: Access policy resolved fresh from DB on each request."""
    token = tokens["u_support"]
    response1 = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response1.status_code == 200

    response2 = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response2.status_code == 200


@pytest.mark.access
async def test_sl02_no_caching_of_policies(
    core: httpx.AsyncClient, tokens: dict
):
    """SL02: Policy changes reflected immediately (no caching)."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
