"""Tests for user management endpoints."""
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_users_unauthorized(client: AsyncClient):
    """Test listing users without authorization."""
    response = await client.get("/api/admin/users")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_users_authorized(client: AsyncClient, admin_headers: dict):
    """Test listing users with authorization."""
    response = await client.get(
        "/api/admin/users",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, admin_headers: dict, db_session):
    """Test creating a user."""
    response = await client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": "newuser@example.com",
            "oauth_sub": "new-sub",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["oauth_sub"] == "new-sub"
    assert data["active"] is True
    assert data["roles"] == []
    assert data["policies"] == []


@pytest.mark.asyncio
async def test_create_user_duplicate_email(
    client: AsyncClient, admin_headers: dict, admin_user
):
    """Test creating user with duplicate email."""
    admin, _ = admin_user
    response = await client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": admin.email,
            "oauth_sub": "different-sub",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_user_duplicate_oauth_sub(
    client: AsyncClient, admin_headers: dict, admin_user
):
    """Test creating user with duplicate oauth_sub."""
    admin, _ = admin_user
    response = await client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": "different@example.com",
            "oauth_sub": admin.oauth_sub,
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient, admin_headers: dict, admin_user):
    """Test getting a user."""
    admin, _ = admin_user
    response = await client.get(
        f"/api/admin/users/{admin.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(admin.id)
    assert data["email"] == admin.email


@pytest.mark.asyncio
async def test_get_nonexistent_user(
    client: AsyncClient, admin_headers: dict
):
    """Test getting a nonexistent user."""
    response = await client.get(
        f"/api/admin/users/{uuid4()}",
        headers=admin_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user_active(
    client: AsyncClient, admin_headers: dict, admin_user, db_session
):
    """Test updating user active status."""
    admin, _ = admin_user
    response = await client.patch(
        f"/api/admin/users/{admin.id}",
        headers=admin_headers,
        json={"active": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is False


@pytest.mark.asyncio
async def test_assign_role_to_user(
    client: AsyncClient, admin_headers: dict, admin_user, db_session
):
    """Test assigning a role to a user."""
    from app.models.system import Role, User
    from sqlalchemy import select

    admin, _ = admin_user
    
    # Create a new role
    test_role = Role(id=uuid4(), name="test_role")
    db_session.add(test_role)
    await db_session.commit()

    # Create a new user
    new_user = User(
        id=uuid4(),
        email="testuser@example.com",
        oauth_sub="test-sub",
        active=True,
    )
    db_session.add(new_user)
    await db_session.commit()

    # Assign role
    response = await client.post(
        f"/api/admin/users/{new_user.id}/roles",
        headers=admin_headers,
        json={"role_id": str(test_role.id)},
    )
    assert response.status_code == 201
    assert "successfully" in response.json()["message"]


@pytest.mark.asyncio
async def test_assign_nonexistent_role(
    client: AsyncClient, admin_headers: dict, admin_user
):
    """Test assigning a nonexistent role."""
    admin, _ = admin_user
    response = await client.post(
        f"/api/admin/users/{admin.id}/roles",
        headers=admin_headers,
        json={"role_id": str(uuid4())},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_revoke_role_from_user(
    client: AsyncClient, admin_headers: dict, admin_user
):
    """Test revoking a role from a user."""
    admin, admin_role = admin_user
    response = await client.delete(
        f"/api/admin/users/{admin.id}/roles/{admin_role.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "successfully" in response.json()["message"]


@pytest.mark.asyncio
async def test_add_user_policy(
    client: AsyncClient, admin_headers: dict, admin_user
):
    """Test adding a policy to a user."""
    admin, _ = admin_user
    response = await client.post(
        f"/api/admin/users/{admin.id}/policies",
        headers=admin_headers,
        json={
            "table_pattern": "users_*",
            "policy_type": "grant",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["table_pattern"] == "users_*"
    assert data["policy_type"] == "grant"


@pytest.mark.asyncio
async def test_add_user_policy_invalid_type(
    client: AsyncClient, admin_headers: dict, admin_user
):
    """Test adding a policy with invalid type."""
    admin, _ = admin_user
    response = await client.post(
        f"/api/admin/users/{admin.id}/policies",
        headers=admin_headers,
        json={
            "table_pattern": "users_*",
            "policy_type": "invalid",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_remove_user_policy(
    client: AsyncClient, admin_headers: dict, admin_user, db_session
):
    """Test removing a policy from a user."""
    from app.models.system import UserPolicy

    admin, _ = admin_user
    
    # Create a policy
    policy = UserPolicy(
        id=uuid4(),
        user_id=admin.id,
        table_pattern="users_*",
        policy_type="grant",
    )
    db_session.add(policy)
    await db_session.commit()

    # Remove policy
    response = await client.delete(
        f"/api/admin/users/{admin.id}/policies/{policy.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "successfully" in response.json()["message"]
