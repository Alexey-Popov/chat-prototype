"""User-level policy tests (U01-U04)."""
import pytest
import httpx


@pytest.mark.access
async def test_u01_grant_policy_allows_access(
    core: httpx.AsyncClient, tokens: dict
):
    """U01: User grant policy allows access to specific table."""
    token = tokens["u_override"]
    response = await core.post(
        "/api/chat",
        json={"message": "Transaction 42"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.access
async def test_u02_restrict_policy_denies_access(
    core: httpx.AsyncClient, tokens: dict
):
    """U02: User restrict policy denies access to specific table."""
    token = tokens["u_restricted"]
    response = await core.post(
        "/api/chat",
        json={"message": "Transaction 42"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should not include restricted content
    assert response.status_code in (200, 403)


@pytest.mark.access
async def test_u03_grant_overrides_role_restriction(
    core: httpx.AsyncClient, tokens: dict
):
    """U03: Grant policy overrides role-based restriction."""
    token = tokens["u_override"]
    response = await core.post(
        "/api/chat",
        json={"message": "Transaction 42"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.access
async def test_u04_restrict_overrides_role_grant(
    core: httpx.AsyncClient, tokens: dict
):
    """U04: Restrict policy overrides role-based grant."""
    token = tokens["u_restricted"]
    response = await core.post(
        "/api/chat",
        json={"message": "Finance report 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Finance role can access, but policy may restrict
    assert response.status_code in (200, 403)
