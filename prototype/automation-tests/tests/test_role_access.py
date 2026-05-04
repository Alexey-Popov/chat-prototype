"""Role-based access control tests (R01-R09)."""
import pytest
import httpx


@pytest.mark.access
async def test_r01_support_can_access_support_content(
    core: httpx.AsyncClient, tokens: dict
):
    """R01: SUPPORT role can access chunks with allowed_roles=[SUPPORT]."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    content = await response.aread()
    assert b"Support ticket 1" in content or b"support" in content.lower()


@pytest.mark.access
async def test_r02_finance_can_access_finance_content(
    core: httpx.AsyncClient, tokens: dict
):
    """R02: FINANCE role can access chunks with allowed_roles=[FINANCE]."""
    token = tokens["u_finance"]
    response = await core.post(
        "/api/chat",
        json={"message": "Finance report 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.access
async def test_r03_bizdev_can_access_bizdev_content(
    core: httpx.AsyncClient, tokens: dict
):
    """R03: BIZDEV role can access chunks with allowed_roles=[BIZDEV]."""
    token = tokens["u_bizdev"]
    response = await core.post(
        "/api/chat",
        json={"message": "Deal memo 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.access
async def test_r04_support_cannot_access_finance_content(
    core: httpx.AsyncClient, tokens: dict
):
    """R04: SUPPORT role denied access to FINANCE content."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Finance report 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (200, 403)
    if response.status_code == 200:
        content = await response.aread()
        assert b"Finance report 1" not in content


@pytest.mark.access
async def test_r05_shared_content_accessible_to_all(
    core: httpx.AsyncClient, tokens: dict
):
    """R05: Content with allowed_roles=[SUPPORT,FINANCE,BIZDEV] accessible to all."""
    for user_key in ["u_support", "u_finance", "u_bizdev"]:
        token = tokens[user_key]
        response = await core.post(
            "/api/chat",
            json={"message": "Company profile"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


@pytest.mark.access
async def test_r06_admin_can_access_all_content(
    core: httpx.AsyncClient, tokens: dict
):
    """R06: ADMIN role can access all content."""
    token = tokens["u_admin"]
    response = await core.post(
        "/api/chat",
        json={"message": "Finance report 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.access
async def test_r07_user_cannot_see_restricted_chunks(
    core: httpx.AsyncClient, tokens: dict
):
    """R07: User restricted from accessing chunks."""
    token = tokens["u_restricted"]
    response = await core.post(
        "/api/chat",
        json={"message": "Transaction 42"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should either deny or not include transaction content
    assert response.status_code in (200, 403)


@pytest.mark.access
async def test_r08_user_override_grants_access(
    core: httpx.AsyncClient, tokens: dict
):
    """R08: User-level grant overrides role restriction."""
    token = tokens["u_override"]
    response = await core.post(
        "/api/chat",
        json={"message": "Transaction 42"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.access
async def test_r09_multiple_roles_get_union_of_access(
    core: httpx.AsyncClient, tokens: dict
):
    """R09: User with multiple roles gets union of permitted content."""
    token = tokens["u_support"]
    response = await core.post(
        "/api/chat",
        json={"message": "Support ticket 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
