"""JWT validation module."""
from typing import Optional
from datetime import datetime, timedelta

from jose import JWTError, jwt
from app.config import settings


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None


def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token.
    
    Args:
        data: Data to encode in token
        expires_delta: Token expiration time delta
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt
