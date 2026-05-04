"""Authentication endpoints"""
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from authlib.integrations.httpx_client import AsyncOAuth2Client
import httpx
from pydantic import BaseModel
from app.config import settings
from app.db import get_system_db
from app.models import User, Role, UserRole
from app.core.jwt import create_jwt_token

router = APIRouter()


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.get("/login")
async def oauth_login():
    """Return the OAuth provider's authorization URL."""
    if settings.oauth_provider == "google":
        async with AsyncOAuth2Client(
            client_id=settings.oauth_client_id,
            redirect_uri="http://localhost:8000/auth/callback",
            scope="openid email profile",
        ) as client:
            uri, _ = client.create_authorization_url(
                "https://accounts.google.com/o/oauth2/v2/auth"
            )
            return {"authorization_url": uri}
    raise HTTPException(status_code=400, detail="Unsupported OAuth provider")


@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_system_db),
):
    """Handle OAuth provider callback — exchange code for JWT."""
    if settings.oauth_provider != "google":
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")

    try:
        async with AsyncOAuth2Client(
            client_id=settings.oauth_client_id,
            client_secret=settings.oauth_client_secret,
            redirect_uri="http://localhost:8000/auth/callback",
        ) as client:
            token_data = await client.fetch_token(
                "https://oauth2.googleapis.com/token", code=code
            )

        async with httpx.AsyncClient() as http:
            resp = await http.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            user_info = resp.json()

        oauth_sub = user_info.get("id")
        email = user_info.get("email")
        if not oauth_sub or not email:
            raise HTTPException(status_code=400, detail="Invalid OAuth response")

        user = await _find_or_create_user(db, oauth_sub=oauth_sub, email=email)
        role_ids = await _get_role_ids(db, user.id)
        jwt = create_jwt_token(user.id, role_ids, user.email)
        return LoginResponse(access_token=jwt)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OAuth error: {exc}") from exc


@router.get("/dev-login", response_model=LoginResponse)
async def dev_login(
    email: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_system_db),
):
    """
    Dev-only endpoint — bypass OAuth and issue a JWT directly.
    Requires DEV_MOCK_USER to be set (or an explicit ?email= param for test fixtures).
    """
    if not settings.dev_mock_user and not email:
        raise HTTPException(status_code=403, detail="Dev login not enabled")

    resolved_email = email or settings.dev_mock_user
    user = await _find_or_create_user(db, oauth_sub=f"dev|{resolved_email}", email=resolved_email)
    role_ids = await _get_role_ids(db, user.id)
    jwt = create_jwt_token(user.id, role_ids, user.email)
    return LoginResponse(access_token=jwt)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _find_or_create_user(db: AsyncSession, oauth_sub: str, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        user = User(id=uuid4(), oauth_sub=oauth_sub, email=email, active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def _get_role_ids(db: AsyncSession, user_id) -> list:
    result = await db.execute(
        select(UserRole.role_id).where(UserRole.user_id == user_id)
    )
    return [str(row[0]) for row in result.all()]
