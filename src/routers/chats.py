# src/routers/chats.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import parse_obj_as
from uuid import UUID

from src.dependencies import get_async_session, auth_guard
from src.schemas.auth import TokenUserInfo
from src.schemas.chat import (
    ChatListItem,
    ChatsListResponse,
    ChatCreate,
    MessageCreate,
    MessageRead,
)
from src.services import chat_service

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/", response_model=ChatsListResponse)
async def api_list_chats(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_async_session),
    current_user: TokenUserInfo = Depends(auth_guard),
):
    """
    GET /chats?limit=&offset=&sort=asc|desc
    Возвращает { items: [...], total: N }
    Сортировка по времени последнего сообщения (по умолчанию desc).
    """
    try:
        data = await chat_service.list_chats_for_user(
            db=db, user_id=current_user.id, limit=limit, offset=offset, sort=sort
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    items = parse_obj_as(List[ChatListItem], data["items"])
    return ChatsListResponse(items=items, total=data["total"])


@router.post("/", response_model=ChatListItem, status_code=status.HTTP_201_CREATED)
async def api_create_chat(
    payload: ChatCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: TokenUserInfo = Depends(auth_guard),
):
    chat = await chat_service.create_group(db=db, payload=payload, creator_id=current_user.id)
    return parse_obj_as(ChatListItem, chat)


@router.get("/{chat_id}/messages", response_model=List[MessageRead])
async def api_get_messages(
    chat_id: UUID = Path(...),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    current_user: TokenUserInfo = Depends(auth_guard),
):
    # проверим, что текущий пользователь — участник чата
    user_chats = await chat_service.list_chats_for_user(db=db, user_id=current_user.id, limit=1, offset=0)
    # более эффективная проверка — сделать запрос "is member" (можем добавить), но для простоты:
    # тут проверка по всем чатам не идеальна — можно заменить на запрос in chat_members
    # добавим оптимизацию: прямой запрос проверки участия
    from sqlalchemy import text
    check_q = text("""
        SELECT 1 FROM chat_members WHERE chat_id = :chat_id AND user_id = :user_id LIMIT 1
    """)
    res = await db.execute(check_q, {"chat_id": str(chat_id), "user_id": current_user.id})
    if res.first() is None:
        raise HTTPException(status_code=403, detail="You are not a member of this chat")

    messages = await chat_service.get_messages(db=db, chat_id=str(chat_id), limit=limit, offset=offset)
    return parse_obj_as(List[MessageRead], messages)


@router.post("/{chat_id}/message", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def api_send_message(
    chat_id: UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: TokenUserInfo = Depends(auth_guard),
):
    # проверка членства
    from sqlalchemy import text
    check_q = text("""
        SELECT 1 FROM chat_members WHERE chat_id = :chat_id AND user_id = :user_id LIMIT 1
    """)
    res = await db.execute(check_q, {"chat_id": str(chat_id), "user_id": current_user.id})
    if res.first() is None:
        raise HTTPException(status_code=403, detail="You are not a member of this chat")

    message = await chat_service.send_message(db=db, chat_id=str(chat_id), payload=payload, sender_id=current_user.id)
    if message is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return parse_obj_as(MessageRead, message)