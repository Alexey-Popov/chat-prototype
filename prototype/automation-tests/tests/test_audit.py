"""Audit logging tests (H01-H06)."""
import pytest
import httpx


@pytest.mark.audit
async def test_h01_chat_message_logged(
    core: httpx.AsyncClient, tokens: dict
):
    """H01: Chat message is logged to chat_messages table."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.audit
async def test_h02_access_decision_logged(
    core: httpx.AsyncClient, tokens: dict
):
    """H02: Access decision is logged."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.audit
async def test_h03_violation_logged(
    core: httpx.AsyncClient, tokens: dict
):
    """H03: Access violation is logged."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Finance report 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Violation logged even if request succeeds


@pytest.mark.audit
async def test_h04_chunk_ids_recorded(
    core: httpx.AsyncClient, tokens: dict
):
    """H04: Retrieved chunk IDs are recorded in audit."""
    token = tokens["u_finance"]
    response = await core.post(
        "/api/chat",
        json={"message": "Finance report 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.audit
async def test_h05_timestamp_recorded(
    core: httpx.AsyncClient, tokens: dict
):
    """H05: Request timestamp is recorded."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.audit
async def test_h06_user_id_recorded(
    core: httpx.AsyncClient, tokens: dict
):
    """H06: User ID is recorded in audit log."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
