from typing import List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import src.queries.chat_queries as chat_queries
from src.schemas.chat import (
    ChatInfo,
    ChatInfoDto,
    CreateChatDto,
    MessageInfoDto,
    SendMessageDto,
)


async def get_chats_for_user(
    db: AsyncSession, user_id: str, limit: int = 20, offset: int = 0
) -> List[ChatInfoDto]:
    return await chat_queries.get_chats_for_user(
        db, user_id=user_id, limit=limit, offset=offset
    )


async def create_chat(
    db: AsyncSession, payload: CreateChatDto, creator_id: str
) -> dict:
    if payload.type == "group" and not payload.title:
        raise HTTPException(400, "Title is required for groups")
    if (
        payload.type == "direct"
        and len([member for member in payload.members if member != creator_id])
        != 1
    ):
        raise HTTPException(400, "One member must be provided for direct chats")

    chat: ChatInfo = await chat_queries.create_chat(
        db,
        type_=payload.type,
        title=(payload.title if payload.type != "direct" else None),
    )

    await chat_queries.add_chat_member(
        db, chat_id=chat.id, user_id=creator_id, role="admin"
    )
    # добавляем остальных участников как member (если есть)
    for uid in payload.members:
        # не перезаписываем роль создателя
        if str(uid) == str(creator_id):
            continue
        await chat_queries.add_chat_member(
            db, chat_id=chat.id, user_id=str(uid), role="member"
        )
    return chat


async def get_messages(
    db: AsyncSession, chat_id: str, limit: int = 100, offset: int = 0
) -> List[MessageInfoDto]:
    return await chat_queries.get_messages_for_chat(
        db, chat_id=chat_id, limit=limit, offset=offset
    )


async def send_message(
    db: AsyncSession,
    chat_id: str,
    payload: SendMessageDto,
    sender_id: str,
) -> MessageInfoDto:
    return await chat_queries.send_message(
        db,
        chat_id=chat_id,
        text_=payload.text,
        sender_id=sender_id,
        replies_to=payload.replies_to,
    )


async def is_user_in_chat(db: AsyncSession, chat_id: str, user_id) -> bool:
    return await chat_queries.is_user_in_chat(
        db=db, chat_id=chat_id, user_id=user_id
    )


async def get_chats_total(db: AsyncSession, user_id: str) -> int:
    return await chat_queries.get_chats_total(db=db, user_id=user_id)


async def get_messages_total(db: AsyncSession, chat_id: str) -> int:
    return await chat_queries.get_messages_total(db=db, chat_id=chat_id)

async def rename_chat(db: AsyncSession, chat_id: str, title: str) -> ChatInfo:
    return await chat_queries.update_chat_title(db, chat_id, title)


async def edit_message(
    db: AsyncSession, message_id: str, user_id: str, text: str
) -> MessageInfoDto:
    return await chat_queries.update_message(
        db, message_id=message_id, user_id=user_id, text_=text
    )


async def list_members(db: AsyncSession, chat_id: str):
    return await chat_queries.get_chat_members(db, chat_id)


async def delete_member(db: AsyncSession, chat_id: str, target_user_id: str):
    return await chat_queries.remove_chat_member(
        db, chat_id=chat_id, user_id=target_user_id
    )
