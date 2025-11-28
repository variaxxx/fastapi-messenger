from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.chat import ChatCreate, MessageCreate
from src import queries as q_module  # если надо будет
from src.queries import chat_queries

MAX_LIMIT = 1000
DEFAULT_LIMIT = 50


async def list_chats_for_user(
    db: AsyncSession,
    user_id: str,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    sort: str = "desc",
) -> Dict[str, Any]:
    # валидация limit/offset/sort
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT
    if offset < 0:
        offset = 0

    order = "DESC" if sort.lower() != "asc" else "ASC"

    total = await chat_queries.count_chats_for_user(db, user_id=user_id)
    items = await chat_queries.get_chats_for_user_paginated(db, user_id=user_id, limit=limit, offset=offset, order=order)
    return {"total": total, "items": items}


async def create_group(db: AsyncSession, payload: ChatCreate, creator_id: str) -> dict:
    chat = await chat_queries.create_chat(db, type_=payload.type, title=payload.title)
    # добавляем создателя как admin
    await chat_queries.add_chat_member(db, chat_id=chat["id"], user_id=creator_id, role="admin")
    # добавляем остальных участников (если есть)
    if payload.members:
        for uid in payload.members:
            if str(uid) == str(creator_id):
                continue
            await chat_queries.add_chat_member(db, chat_id=chat["id"], user_id=str(uid), role="member")
    return chat


async def get_messages(db: AsyncSession, chat_id: str, limit: int = 100, offset: int = 0):
    return await chat_queries.get_messages_for_chat(db, chat_id=chat_id, limit=limit, offset=offset)


async def send_message(db: AsyncSession, chat_id: str, payload: MessageCreate, sender_id: Optional[str]):
    # можно добавить проверку прав (что sender_id в members) здесь или в роутере
    return await chat_queries.create_message(db, chat_id=chat_id, text_=payload.text, sender_id=sender_id, replies_to=payload.replies_to)