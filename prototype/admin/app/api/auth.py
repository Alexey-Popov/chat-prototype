"""Dev / auth helpers for the admin API."""

from datetime import timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.jwt import create_token
from app.db import get_db
from app.models.system import Role, User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.get("/dev-login", response_model=LoginResponse)
async def dev_login(
    email: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Dev-only: issue a JWT for a user that has the **admin** role (create user/role as needed).
    Mirrors core `DEV_MOCK_USER` — set `DEV_MOCK_USER` in `.env` or pass `?email=`.
    """
    if not settings.dev_mock_user and not email:
        raise HTTPException(status_code=403, detail="Dev login not enabled")

    resolved_email = email or settings.dev_mock_user
    assert resolved_email is not None

    user = await _find_or_create_user(db, oauth_sub=f"dev|{resolved_email}", email=resolved_email)
    admin_role = await _ensure_admin_role_row(db)
    await _ensure_user_admin_link(db, user.id, admin_role.id)

    result = await db.execute(
        select(UserRole.role_id).where(UserRole.user_id == user.id)
    )
    role_ids = [str(row[0]) for row in result.all()]

    token = create_token(
        {
            "sub": str(user.id),
            "role_ids": role_ids,
            "email": user.email,
        },
        expires_delta=timedelta(hours=24),
    )
    return LoginResponse(access_token=token)


async def _find_or_create_user(db: AsyncSession, oauth_sub: str, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        user = User(id=uuid4(), oauth_sub=oauth_sub, email=email, active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def _ensure_admin_role_row(db: AsyncSession) -> Role:
    result = await db.execute(select(Role).where(Role.name == "admin"))
    role = result.scalars().first()
    if role:
        return role
    role = Role(id=uuid4(), name="admin")
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def _ensure_user_admin_link(db: AsyncSession, user_id, admin_role_id) -> None:
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == admin_role_id,
        )
    )
    if result.scalars().first():
        return
    db.add(UserRole(user_id=user_id, role_id=admin_role_id))
    await db.commit()
