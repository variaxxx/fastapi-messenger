from typing import AsyncGenerator

from fastapi import HTTPException, Request, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import websocket_manager
from src.core.security import decode_jwt
from src.db.database import async_session_maker
from src.schemas.auth import TokenUserInfo


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise


def auth_guard(request: Request) -> TokenUserInfo:
    token = extract_bearer_token(request)
    payload = decode_jwt(token)
    return TokenUserInfo.model_validate(payload.get("user"))


async def socket_auth_guard(websocket: WebSocket) -> str:
    header = websocket.headers.get("authorization")
    if not header or not header.startswith("Bearer "):
        await websocket_manager.send_error("Invalid token", websocket)

    token = header.split()[1]
    payload = decode_jwt(token)
    return TokenUserInfo.model_validate(payload.get("user"))


def extract_bearer_token(request: Request) -> str:
    header = request.headers.get("authorization")
    if not header or not header.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized")

    token = header.split()[1]
    return token
