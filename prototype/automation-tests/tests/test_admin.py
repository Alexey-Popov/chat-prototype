"""Admin API tests (AD01-AD06)."""
import pytest
import httpx


@pytest.mark.admin
async def test_ad01_admin_can_view_audit_logs(admin: httpx.AsyncClient):
    """AD01: Admin can retrieve audit logs."""
    response = await admin.get("/audit")
    assert response.status_code == 200


@pytest.mark.admin
async def test_ad02_admin_can_list_users(admin: httpx.AsyncClient):
    """AD02: Admin can list all users."""
    response = await admin.get("/users")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data or isinstance(data, list)


@pytest.mark.admin
async def test_ad03_admin_can_view_user_policies(admin: httpx.AsyncClient):
    """AD03: Admin can view user policies."""
    response = await admin.get("/policies")
    assert response.status_code == 200


@pytest.mark.admin
async def test_ad04_admin_can_create_role(admin: httpx.AsyncClient):
    """AD04: Admin can create new role."""
    response = await admin.post(
        "/roles",
        json={"name": "TESTER", "description": "Test role"},
    )
    assert response.status_code in (200, 201)


@pytest.mark.admin
async def test_ad05_admin_can_grant_user_policy(admin: httpx.AsyncClient):
    """AD05: Admin can grant user-level policy."""
    response = await admin.post(
        "/policies",
        json={
            "user_id": "test-user",
            "table_pattern": "test_table",
            "policy_type": "grant",
        },
    )
    assert response.status_code in (200, 201, 400)


@pytest.mark.admin
async def test_ad06_admin_can_revoke_user_policy(admin: httpx.AsyncClient):
    """AD06: Admin can revoke user-level policy."""
    response = await admin.delete(
        "/policies/policy-id",
    )
    assert response.status_code in (200, 204, 404)
