from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

import src.services.chat as chats_service
from src.dependencies import auth_guard, get_async_session
from src.response import FindManyResponse
from src.schemas.auth import TokenUserInfo
from src.schemas.chat import (
    ChatInfo,
    ChatInfoDto,
    CreateChatDto,
    MessageInfoDto,
    SendMessageDto,
)

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.get("/", response_model=FindManyResponse[ChatInfoDto])
async def api_list_chats(
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    chats = await chats_service.get_chats_for_user(
        db, user_id=user.id, limit=limit, offset=offset
    )
    total = await chats_service.get_chats_total(db, user_id=user.id)
    return FindManyResponse[ChatInfoDto](
        total=total, count=len(chats), items=chats
    )


@router.post(
    "/", response_model=ChatInfoDto, status_code=status.HTTP_201_CREATED
)
async def api_create_chat(
    payload: CreateChatDto,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    chat: ChatInfo = await chats_service.create_chat(
        db, payload, creator_id=user.id
    )
    return ChatInfoDto(
        id=chat.id,
        type=chat.type,
        title=chat.title,
        role="admin",
        last_message_id=None,
        last_message_date=None,
        last_message_text=None,
        last_message_sender=None,
    )


@router.get(
    "/{chat_id}/messages", response_model=FindManyResponse[MessageInfoDto]
)
async def api_get_messages(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    chat_id: UUID4,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if not await chats_service.is_user_in_chat(
        db, chat_id=chat_id, user_id=user.id
    ):
        raise HTTPException(
            status_code=403, detail="You are not a member of this chat"
        )

    messages = await chats_service.get_messages(
        db, chat_id=str(chat_id), limit=limit, offset=offset
    )
    total = await chats_service.get_messages_total(db=db, chat_id=chat_id)
    return FindManyResponse[MessageInfoDto](
        total=total, count=len(messages), items=messages
    )


@router.post(
    "/{chat_id}/message",
    response_model=MessageInfoDto,
    status_code=status.HTTP_201_CREATED,
)
async def api_send_message(
    chat_id: UUID4,
    payload: SendMessageDto,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
):
    if not await chats_service.is_user_in_chat(
        db, chat_id=chat_id, user_id=user.id
    ):
        raise HTTPException(
            status_code=403, detail="You are not a member of this chat"
        )

    message: MessageInfoDto = await chats_service.send_message(
        db, chat_id=chat_id, payload=payload, sender_id=user.id
    )
    return message
