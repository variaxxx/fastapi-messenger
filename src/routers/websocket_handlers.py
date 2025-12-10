from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

import src.services.chat as chat_service
from src.core.websocket_manager import WebSocketManager
from src.schemas.auth import TokenUserInfo
from src.schemas.websocket import (
    MessageReadPayload,
    SendMessagePayload,
    UserTypingPayload,
)

websocket_manager = WebSocketManager()


@websocket_manager.handler("message:send")
async def message_send(
    db: AsyncSession, payload: dict, user: TokenUserInfo, websocket: WebSocket
):
    payload = SendMessagePayload(**payload)

    await chat_service.send_message(
        db=db,
        chat_id=payload.chat_id,
        text=payload.text,
        replies_to=payload.replies_to,
        sender_id=user.id,
        attachments=[],
    )


@websocket_manager.handler("message:read")
async def message_read(
    db: AsyncSession, payload: dict, user: TokenUserInfo, websocket: WebSocket
):
    payload = MessageReadPayload(**payload)

    await chat_service.mark_message_read(
        db=db,
        user_id=user.id,
        chat_id=payload.chat_id,
        message_id=payload.message_id,
    )


@websocket_manager.handler("user:typing")
async def user_typing(
    db: AsyncSession, payload: dict, user: TokenUserInfo, websocket: WebSocket
):
    payload = UserTypingPayload(**payload)

    await websocket_manager.broadcast_to_chat(
        chat_id=payload.chat_id,
        event="user:typing",
        message={"chat_id": payload.chat_id, "user_id": user.id},
    )
