"""JWT token creation and verification"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from jose import JWTError, jwt
from pydantic import BaseModel
from app.config import settings


class TokenData(BaseModel):
    """JWT token payload"""

    sub: str  # user_id
    role_ids: list[str]  # role UUIDs
    email: str
    exp: datetime


def create_jwt_token(
    user_id: UUID,
    role_ids: list[UUID],
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT token"""
    if expires_delta is None:
        expires_delta = timedelta(seconds=settings.jwt_expiry_seconds)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": str(user_id),
        "role_ids": [str(rid) for rid in role_ids],
        "email": email,
        "exp": int(expire.timestamp()),
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def verify_jwt_token(token: str) -> TokenData:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        role_ids: list[str] = payload.get("role_ids", [])
        email: str = payload.get("email")
        exp: int = payload.get("exp")

        if not user_id or not email:
            raise JWTError("Invalid token payload")

        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        return TokenData(sub=user_id, role_ids=role_ids, email=email, exp=exp_dt)
    except JWTError:
        raise JWTError("Invalid token")
