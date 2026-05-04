"""Unit tests for PolicyEngine."""
import pytest
from uuid import uuid4
from app.models import User, Role, UserRole, RolePolicy, UserPolicy
from app.access.policy_engine import PolicyEngine


async def test_policy_engine_resolve_with_roles(test_system_db):
    """Role policies are included in the resolved set."""
    async with test_system_db() as db:
        user = User(id=uuid4(), oauth_sub="u1", email="u1@test.com", active=True)
        role = Role(id=uuid4(), name="analyst")
        db.add(user)
        db.add(role)
        await db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.add(RolePolicy(id=uuid4(), role_id=role.id, table_pattern="analytics_data"))
        await db.commit()

        patterns = await PolicyEngine.resolve(user.id, db)

    assert "analytics_data" in patterns


async def test_policy_engine_user_grant_adds_pattern(test_system_db):
    """User grant policy adds a table pattern beyond the role."""
    async with test_system_db() as db:
        user = User(id=uuid4(), oauth_sub="u2", email="u2@test.com", active=True)
        db.add(user)
        await db.flush()
        db.add(UserPolicy(id=uuid4(), user_id=user.id, table_pattern="special_data", policy_type="grant"))
        await db.commit()

        patterns = await PolicyEngine.resolve(user.id, db)

    assert "special_data" in patterns


async def test_policy_engine_user_restrict_removes_pattern(test_system_db):
    """User restrict policy removes a table pattern the role would otherwise allow."""
    async with test_system_db() as db:
        user = User(id=uuid4(), oauth_sub="u3", email="u3@test.com", active=True)
        role = Role(id=uuid4(), name="viewer")
        db.add(user)
        db.add(role)
        await db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.add(RolePolicy(id=uuid4(), role_id=role.id, table_pattern="all_data"))
        db.add(UserPolicy(id=uuid4(), user_id=user.id, table_pattern="all_data", policy_type="restrict"))
        await db.commit()

        patterns = await PolicyEngine.resolve(user.id, db)

    assert "all_data" not in patterns


async def test_policy_engine_no_roles_returns_empty(test_system_db):
    """User with no roles and no user policies gets empty set."""
    async with test_system_db() as db:
        user = User(id=uuid4(), oauth_sub="u4", email="u4@test.com", active=True)
        db.add(user)
        await db.commit()

        patterns = await PolicyEngine.resolve(user.id, db)

    assert patterns == set()


async def test_policy_engine_multiple_roles_merged(test_system_db):
    """Patterns from multiple roles are unioned together."""
    async with test_system_db() as db:
        user = User(id=uuid4(), oauth_sub="u5", email="u5@test.com", active=True)
        r1 = Role(id=uuid4(), name="role_a")
        r2 = Role(id=uuid4(), name="role_b")
        db.add_all([user, r1, r2])
        await db.flush()
        db.add(UserRole(user_id=user.id, role_id=r1.id))
        db.add(UserRole(user_id=user.id, role_id=r2.id))
        db.add(RolePolicy(id=uuid4(), role_id=r1.id, table_pattern="table_a"))
        db.add(RolePolicy(id=uuid4(), role_id=r2.id, table_pattern="table_b"))
        await db.commit()

        patterns = await PolicyEngine.resolve(user.id, db)

    assert "table_a" in patterns
    assert "table_b" in patterns
