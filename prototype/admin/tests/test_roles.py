"""Tests for role management endpoints."""
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_roles(client: AsyncClient, admin_headers: dict):
    """Test listing roles."""
    response = await client.get(
        "/api/admin/roles",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1  # At least admin role


@pytest.mark.asyncio
async def test_create_role(client: AsyncClient, admin_headers: dict):
    """Test creating a role."""
    response = await client.post(
        "/api/admin/roles",
        headers=admin_headers,
        json={"name": "editor"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "editor"
    assert data["policies"] == []


@pytest.mark.asyncio
async def test_create_role_duplicate(
    client: AsyncClient, admin_headers: dict, admin_user
):
    """Test creating a role with duplicate name."""
    _, admin_role = admin_user
    response = await client.post(
        "/api/admin/roles",
        headers=admin_headers,
        json={"name": admin_role.name},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_role_policy(
    client: AsyncClient, admin_headers: dict, admin_user
):
    """Test adding a policy to a role."""
    _, admin_role = admin_user
    response = await client.post(
        f"/api/admin/roles/{admin_role.id}/policies",
        headers=admin_headers,
        json={"table_pattern": "users_*"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["table_pattern"] == "users_*"


@pytest.mark.asyncio
async def test_add_role_policy_nonexistent_role(
    client: AsyncClient, admin_headers: dict
):
    """Test adding a policy to a nonexistent role."""
    response = await client.post(
        f"/api/admin/roles/{uuid4()}/policies",
        headers=admin_headers,
        json={"table_pattern": "users_*"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_role_policy(
    client: AsyncClient, admin_headers: dict, admin_user, db_session
):
    """Test removing a policy from a role."""
    from app.models.system import RolePolicy

    _, admin_role = admin_user
    
    # Create a policy
    policy = RolePolicy(
        id=uuid4(),
        role_id=admin_role.id,
        table_pattern="users_*",
    )
    db_session.add(policy)
    await db_session.commit()

    # Remove policy
    response = await client.delete(
        f"/api/admin/roles/{admin_role.id}/policies/{policy.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "successfully" in response.json()["message"]
