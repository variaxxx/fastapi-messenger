from typing import AsyncGenerator

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decode_jwt
from src.db.database import async_session_maker
from src.schemas.auth import TokenPayload


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


def auth_guard(request: Request) -> TokenPayload:
    token = extract_bearer_token(request)
    payload = decode_jwt(token)
    return payload


def extract_bearer_token(request: Request) -> str:
    header = request.headers.get("authorization")
    if not header or not header.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized")

    token = header.split()[1]
    return token
