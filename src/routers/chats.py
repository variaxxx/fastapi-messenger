# src/routers/chats.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.chat import ChatCreate, ChatRead, MessageCreate, MessageRead
from src.services.chat_service import list_chats_for_user, create_group, get_messages, send_message
from src.dependencies import get_async_session, auth_guard
from src.schemas.auth import TokenUserInfo

from pydantic import parse_obj_as
from uuid import UUID

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/", response_model=List[ChatRead])
async def api_list_chats(
    db: AsyncSession = Depends(get_async_session),
    current_user: TokenUserInfo = Depends(auth_guard),
):
    """
    GET /chats - получить список чатов, где текущий пользователь — участник
    """
    chats = await list_chats_for_user(db, user_id=current_user.id)
    # pydantic-валидация преобразует поля (например timestamps)
    return parse_obj_as(List[ChatRead], chats)


@router.post("/", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
async def api_create_chat(
    payload: ChatCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: TokenUserInfo = Depends(auth_guard),
):
    """
    POST /chats - создать группу (type: 'group' или 'direct')
    """
    chat = await create_group(db, payload, creator_id=current_user.id)
    return ChatRead.model_validate(chat)


@router.get("/{chat_id}/messages", response_model=List[MessageRead])
async def api_get_messages(
    chat_id: UUID = Path(...),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    current_user: TokenUserInfo = Depends(auth_guard),
):
    """
    GET /chats/{chat_id}/messages - получить сообщения чата
    Только участники могут видеть сообщения.
    """
    # проверка участия — запроса на список чатов юзера будет достаточно
    chats = await list_chats_for_user(db, user_id=current_user.id)
    if not any(str(c["id"]) == str(chat_id) for c in chats):
        raise HTTPException(status_code=403, detail="You are not a member of this chat")

    messages = await get_messages(db, chat_id=str(chat_id), limit=limit, offset=offset)
    if messages is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return parse_obj_as(List[MessageRead], messages)


@router.post("/{chat_id}/message", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def api_send_message(
    chat_id: UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: TokenUserInfo = Depends(auth_guard),
):
    """
    POST /chats/{chat_id}/message - страховочный эндпоинт для отправки сообщения
    """
    # проверяем, что пользователь — участник чата
    chats = await list_chats_for_user(db, user_id=current_user.id)
    if not any(str(c["id"]) == str(chat_id) for c in chats):
        raise HTTPException(status_code=403, detail="You are not a member of this chat")

    message = await send_message(db, chat_id=str(chat_id), payload=payload, sender_id=current_user.id)
    if message is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return MessageRead.model_validate(message)
