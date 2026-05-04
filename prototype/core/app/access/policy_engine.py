"""Access policy resolution engine.

Always queries system_db directly — no caching, no JWT payload reuse (P4).
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import UserRole, RolePolicy, UserPolicy


class PolicyEngine:
    @staticmethod
    async def resolve(user_id: UUID, db: AsyncSession) -> set[str]:
        """
        Return the effective set of allowed table patterns for user_id.

        Algorithm:
          1. Union all role_policies for roles assigned to this user
          2. Add any user-level grant policies
          3. Remove any user-level restrict policies
        """
        # Step 1: role-based patterns via explicit join (avoids lazy loading)
        result = await db.execute(
            select(RolePolicy.table_pattern)
            .join(UserRole, UserRole.role_id == RolePolicy.role_id)
            .where(UserRole.user_id == user_id)
        )
        allowed: set[str] = {row[0] for row in result.all()}

        # Step 2+3: user-level overrides
        result = await db.execute(
            select(UserPolicy.table_pattern, UserPolicy.policy_type)
            .where(UserPolicy.user_id == user_id)
        )
        for table_pattern, policy_type in result.all():
            if policy_type == "grant":
                allowed.add(table_pattern)
            elif policy_type == "restrict":
                allowed.discard(table_pattern)

        return allowed
