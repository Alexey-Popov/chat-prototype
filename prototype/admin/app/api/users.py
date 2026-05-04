"""Users management API endpoints."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.deps import get_admin_user
from app.models.system import User, UserRole, Role, UserPolicy

router = APIRouter(prefix="/api/admin", tags=["users"])


# ============================================================================
# Pydantic Models
# ============================================================================


class UserCreateRequest(BaseModel):
    """Create user request."""

    email: EmailStr
    oauth_sub: str


class UserUpdateRequest(BaseModel):
    """Update user request."""

    active: bool


class UserRoleAssignRequest(BaseModel):
    """Assign role request."""

    role_id: UUID


class UserPolicyRequest(BaseModel):
    """User policy request."""

    table_pattern: str
    policy_type: str  # 'grant' | 'restrict'


class UserRoleResponse(BaseModel):
    """User role response."""

    id: UUID
    name: str

    class Config:
        from_attributes = True


class UserPolicyResponse(BaseModel):
    """User policy response."""

    id: UUID
    table_pattern: str
    policy_type: str

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    """User detail response."""

    id: UUID
    email: str
    oauth_sub: str
    active: bool
    roles: List[UserRoleResponse]
    policies: List[UserPolicyResponse]

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response."""

    id: UUID
    email: str
    oauth_sub: str
    active: bool
    created_at: str

    class Config:
        from_attributes = True


class PaginatedUsersResponse(BaseModel):
    """Paginated users response."""

    items: List[UserListResponse]
    total: int
    page: int
    size: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/users", response_model=PaginatedUsersResponse)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedUsersResponse:
    """List all users with pagination."""
    offset = (page - 1) * size

    # Count total
    result = await db.execute(select(func.count(User.id)))
    total = result.scalar() or 0

    # Fetch users
    result = await db.execute(
        select(User)
        .order_by(desc(User.created_at))
        .offset(offset)
        .limit(size)
    )
    users = result.scalars().all()

    return PaginatedUsersResponse(
        items=[
            UserListResponse(
                id=u.id,
                email=u.email,
                oauth_sub=u.oauth_sub,
                active=u.active,
                created_at=u.created_at.isoformat(),
            )
            for u in users
        ],
        total=total,
        page=page,
        size=size,
    )


@router.post("/users", response_model=UserDetailResponse)
async def create_user(
    request: UserCreateRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """Create a new user."""
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    result = await db.execute(
        select(User).where(User.oauth_sub == request.oauth_sub)
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this oauth_sub already exists",
        )

    # Create user
    from uuid import uuid4

    user = User(
        id=uuid4(),
        email=request.email,
        oauth_sub=request.oauth_sub,
        active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        oauth_sub=user.oauth_sub,
        active=user.active,
        roles=[],
        policies=[],
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: UUID,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """Get user detail."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Fetch roles
    result = await db.execute(
        select(Role)
        .join(UserRole)
        .where(UserRole.user_id == user_id)
    )
    roles = result.scalars().all()

    # Fetch policies
    result = await db.execute(
        select(UserPolicy).where(UserPolicy.user_id == user_id)
    )
    policies = result.scalars().all()

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        oauth_sub=user.oauth_sub,
        active=user.active,
        roles=[UserRoleResponse(id=r.id, name=r.name) for r in roles],
        policies=[
            UserPolicyResponse(
                id=p.id,
                table_pattern=p.table_pattern,
                policy_type=p.policy_type,
            )
            for p in policies
        ],
    )


@router.patch("/users/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """Update user (active flag only)."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.active = request.active
    await db.commit()
    await db.refresh(user)

    # Fetch roles and policies
    result = await db.execute(
        select(Role)
        .join(UserRole)
        .where(UserRole.user_id == user_id)
    )
    roles = result.scalars().all()

    result = await db.execute(
        select(UserPolicy).where(UserPolicy.user_id == user_id)
    )
    policies = result.scalars().all()

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        oauth_sub=user.oauth_sub,
        active=user.active,
        roles=[UserRoleResponse(id=r.id, name=r.name) for r in roles],
        policies=[
            UserPolicyResponse(
                id=p.id,
                table_pattern=p.table_pattern,
                policy_type=p.policy_type,
            )
            for p in policies
        ],
    )


@router.post("/users/{user_id}/roles", status_code=status.HTTP_201_CREATED)
async def assign_role_to_user(
    user_id: UUID,
    request: UserRoleAssignRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Assign a role to a user."""
    # Verify user exists
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify role exists
    result = await db.execute(
        select(Role).where(Role.id == request.role_id)
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Check if already assigned
    result = await db.execute(
        select(UserRole).where(
            (UserRole.user_id == user_id) & (UserRole.role_id == request.role_id)
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already assigned to user",
        )

    # Assign role
    user_role = UserRole(user_id=user_id, role_id=request.role_id)
    db.add(user_role)
    await db.commit()

    return {"message": "Role assigned successfully"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def revoke_role_from_user(
    user_id: UUID,
    role_id: UUID,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke a role from a user."""
    result = await db.execute(
        select(UserRole).where(
            (UserRole.user_id == user_id) & (UserRole.role_id == role_id)
        )
    )
    user_role = result.scalars().first()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User role not found",
        )

    await db.delete(user_role)
    await db.commit()

    return {"message": "Role revoked successfully"}


@router.post("/users/{user_id}/policies", status_code=status.HTTP_201_CREATED)
async def add_user_policy(
    user_id: UUID,
    request: UserPolicyRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserPolicyResponse:
    """Add a policy to a user."""
    # Verify user exists
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Validate policy_type
    if request.policy_type not in ["grant", "restrict"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="policy_type must be 'grant' or 'restrict'",
        )

    from uuid import uuid4

    policy = UserPolicy(
        id=uuid4(),
        user_id=user_id,
        table_pattern=request.table_pattern,
        policy_type=request.policy_type,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    return UserPolicyResponse(
        id=policy.id,
        table_pattern=policy.table_pattern,
        policy_type=policy.policy_type,
    )


@router.delete("/users/{user_id}/policies/{policy_id}")
async def remove_user_policy(
    user_id: UUID,
    policy_id: UUID,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a policy from a user."""
    result = await db.execute(
        select(UserPolicy).where(
            (UserPolicy.user_id == user_id) & (UserPolicy.id == policy_id)
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
