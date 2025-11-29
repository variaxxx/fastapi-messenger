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
    ChatMemberDto,
    CreateChatDto,
    EditMessageDto,
    MessageInfoDto,
    RenameChatDto,
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


@router.patch("/{chat_id}", response_model=ChatInfoDto)
async def api_rename_chat(
    chat_id: UUID4,
    dto: RenameChatDto,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    if not await chats_service.is_user_in_chat(db, chat_id, user.id):
        raise HTTPException(403, "You are not a member of this chat")

    return await chats_service.rename_chat(
        db, editor_id=user.id, chat_id=chat_id, title=dto.new_title
    )


@router.patch("/messages/{message_id}", response_model=MessageInfoDto)
async def api_edit_message(
    message_id: UUID4,
    dto: EditMessageDto,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    return await chats_service.edit_message(
        db, message_id=str(message_id), user_id=user.id, text=dto.text
    )


@router.get(
    "/{chat_id}/members", response_model=FindManyResponse[ChatMemberDto]
)
async def api_get_members(
    chat_id: UUID4,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if not await chats_service.is_user_in_chat(db, chat_id, user.id):
        raise HTTPException(403, "You are not a member of this chat")

    [members, total] = await chats_service.list_members(
        db, chat_id=str(chat_id), limit=limit, offset=offset
    )

    return FindManyResponse[ChatMemberDto](
        total=total, count=len(members), items=members
    )


@router.delete("/{chat_id}/members/{user_id}", status_code=204)
async def api_delete_member(
    chat_id: UUID4,
    user_id: UUID4,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    # Только админ может удалять
    [members, total] = await chats_service.list_members(
        db, chat_id=str(chat_id)
    )
    me = [member for member in members if member.id == user.id]
    if not me or me[0].role != "admin":
        raise HTTPException(403, "Forbidden")

    if str(user_id) == (user.id):
        raise HTTPException(400, "You can`t kick yourself")

    await chats_service.delete_member(
        db, chat_id=str(chat_id), target_user_id=str(user_id)
    )
