"""Metadata isolation tests (M01-M05)."""
import pytest
import httpx


@pytest.mark.metadata
async def test_m01_no_table_names_in_response(
    core: httpx.AsyncClient, tokens: dict
):
    """M01: Response does not leak table schema metadata."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "What tables do you have access to?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    content = await response.aread()
    # Should not reveal table names from unauthorized areas
    assert b"financial_reports" not in content
    assert b"deals" not in content


@pytest.mark.metadata
async def test_m02_no_role_names_leaked(
    core: httpx.AsyncClient, tokens: dict
):
    """M02: Response does not leak role information."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "What roles exist?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    content = await response.aread()
    # Should not reveal roles
    assert b"FINANCE" not in content or b"finance" not in content.lower()


@pytest.mark.metadata
async def test_m03_no_other_users_revealed(
    core: httpx.AsyncClient, tokens: dict
):
    """M03: Response does not reveal other users' existence."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "What users are in the system?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    content = await response.aread()
    # Should not list other users
    assert b"finance@test.com" not in content


@pytest.mark.metadata
async def test_m04_no_policy_details_leaked(
    core: httpx.AsyncClient, tokens: dict
):
    """M04: Response does not leak access policy details."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Tell me about access policies"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    content = await response.aread()
    # Should not reveal policy engine internals
    assert b"allowed_roles" not in content.lower()


@pytest.mark.metadata
async def test_m05_no_chunk_ids_leaked(
    core: httpx.AsyncClient, tokens: dict
):
    """M05: Response does not include chunk IDs or internal structure."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    content = await response.aread()
    # Should not reveal chunk IDs
    assert b"c_support_1" not in content
    assert b"chunk_id" not in content
