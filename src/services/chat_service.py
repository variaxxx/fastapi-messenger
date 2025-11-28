from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.chat import ChatCreate, MessageCreate

from src.queries.chat_queries import (
    get_chats_for_user,
    create_chat,
    add_chat_member,
    get_messages_for_chat,
    create_message,
    get_chat_by_id,
)


async def list_chats_for_user(db: AsyncSession, user_id: str) -> List[dict]:
    return await get_chats_for_user(db, user_id=user_id)


async def create_group(db: AsyncSession, payload: ChatCreate, creator_id: str) -> dict:
    chat = await create_chat(db, type_=payload.type, title=payload.title)
    # добавляем создателя как admin
    await add_chat_member(db, chat_id=chat["id"], user_id=creator_id, role="admin")
    # добавляем остальных участников как member (если есть)
    if payload.members:
        for uid in payload.members:
            # не перезаписываем роль создателя
            if str(uid) == str(creator_id):
                continue
            await add_chat_member(db, chat_id=chat["id"], user_id=str(uid), role="member")
    return chat


async def get_messages(db: AsyncSession, chat_id: str, limit: int = 100, offset: int = 0) -> Optional[List[dict]]:
    chat = await get_chat_by_id(db, chat_id=chat_id)
    if not chat:
        return None
    return await get_messages_for_chat(db, chat_id=chat_id, limit=limit, offset=offset)


async def send_message(db: AsyncSession, chat_id: str, payload: MessageCreate, sender_id: Optional[str]) -> Optional[dict]:
    chat = await get_chat_by_id(db, chat_id=chat_id)
    if not chat:
        return None
    return await create_message(db, chat_id=chat_id, text_=payload.text, sender_id=sender_id, replies_to=payload.replies_to)
