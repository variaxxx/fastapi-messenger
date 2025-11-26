from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import JWTError, jwt

from src.core.config import settings
from src.schemas.auth import TokenPayload


def create_access_token(user_id: int) -> str:
    payload: TokenPayload = {
        "user": {"id": user_id},
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(
        payload, settings.JWT_ACCESS_SECRET, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(user_id: int) -> str:
    payload = {
        "user": {"id": user_id},
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(
        payload, settings.JWT_REFRESH_SECRET, algorithm=settings.JWT_ALGORITHM
    )


def decode_jwt(token: str, is_refresh_token: bool = False) -> dict:
    try:
        secret = (
            settings.JWT_REFRESH_SECRET
            if is_refresh_token
            else settings.JWT_ACCESS_SECRET
        )
        return jwt.decode(
            token, secret, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        raise HTTPException(401, "Invalid token")
