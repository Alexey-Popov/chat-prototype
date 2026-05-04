"""FastAPI dependency functions"""
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from app.db import get_system_db, get_vector_db
from app.core.jwt import verify_jwt_token
from app.config import settings
from app.models import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_system_db),
) -> tuple[User, list[UUID]]:
    """
    Dependency: Extract and verify JWT token, return user and role_ids.
    Raises HTTPException 403 if token is invalid or user not found.
    """
    try:
        token_data = verify_jwt_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication token",
        )

    user_id = UUID(token_data.sub)

    # Fetch user from database
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user or not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found or inactive",
        )

    role_ids = [UUID(rid) for rid in token_data.role_ids]
    return user, role_ids


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_system_db),
) -> Optional[tuple[User, list[UUID]]]:
    """
    Dependency: Extract and verify JWT token if provided.
    Returns (user, role_ids) or None if no token.
    """
    if not credentials:
        return None

    try:
        token_data = verify_jwt_token(credentials.credentials)
    except JWTError:
        return None

    user_id = UUID(token_data.sub)

    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user or not user.active:
        return None

    role_ids = [UUID(rid) for rid in token_data.role_ids]
    return user, role_ids
