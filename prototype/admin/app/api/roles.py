"""Roles management API endpoints."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.deps import get_admin_user
from app.models.system import User, Role, RolePolicy

router = APIRouter(prefix="/api/admin", tags=["roles"])


# ============================================================================
# Pydantic Models
# ============================================================================


class RoleCreateRequest(BaseModel):
    """Create role request."""

    name: str


class RolePolicyRequest(BaseModel):
    """Role policy request."""

    table_pattern: str


class RolePolicyResponse(BaseModel):
    """Role policy response."""

    id: UUID
    table_pattern: str

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """Role response."""

    id: UUID
    name: str
    policies: List[RolePolicyResponse] = []

    class Config:
        from_attributes = True


class PaginatedRolesResponse(BaseModel):
    """Paginated roles response."""

    items: List[RoleResponse]
    total: int
    page: int
    size: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/roles", response_model=PaginatedRolesResponse)
async def list_roles(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRolesResponse:
    """List all roles with pagination."""
    offset = (page - 1) * size

    # Count total
    result = await db.execute(select(func.count(Role.id)))
    total = result.scalar() or 0

    # Fetch roles
    result = await db.execute(
        select(Role)
        .offset(offset)
        .limit(size)
    )
    roles = result.scalars().all()

    items = []
    for role in roles:
        # Fetch policies for this role
        result = await db.execute(
            select(RolePolicy).where(RolePolicy.role_id == role.id)
        )
        policies = result.scalars().all()

        items.append(
            RoleResponse(
                id=role.id,
                name=role.name,
                policies=[
                    RolePolicyResponse(
                        id=p.id,
                        table_pattern=p.table_pattern,
                    )
                    for p in policies
                ],
            )
        )

    return PaginatedRolesResponse(
        items=items,
        total=total,
        page=page,
        size=size,
    )


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreateRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    """Create a new role."""
    # Check if role already exists
    result = await db.execute(
        select(Role).where(Role.name == request.name)
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists",
        )

    from uuid import uuid4

    role = Role(
        id=uuid4(),
        name=request.name,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return RoleResponse(
        id=role.id,
        name=role.name,
        policies=[],
    )


@router.post("/roles/{role_id}/policies", response_model=RolePolicyResponse, status_code=status.HTTP_201_CREATED)
async def add_role_policy(
    role_id: UUID,
    request: RolePolicyRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> RolePolicyResponse:
    """Add a table pattern policy to a role."""
    # Verify role exists
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    from uuid import uuid4

    policy = RolePolicy(
        id=uuid4(),
        role_id=role_id,
        table_pattern=request.table_pattern,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    return RolePolicyResponse(
        id=policy.id,
        table_pattern=policy.table_pattern,
    )


@router.delete("/roles/{role_id}/policies/{policy_id}")
async def remove_role_policy(
    role_id: UUID,
    policy_id: UUID,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a policy from a role."""
    result = await db.execute(
        select(RolePolicy).where(
            (RolePolicy.role_id == role_id) & (RolePolicy.id == policy_id)
        )
    )
    policy = result.scalars().first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    await db.delete(policy)
    await db.commit()

    return {"message": "Policy removed successfully"}
