from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_chats_for_user(db: AsyncSession, user_id: str) -> List[dict]:
    """
    вернет список чатов, где пользователь является участником.
    """
    q = text(
        """
        SELECT c.id, c.created_at, c.type, c.title
        FROM chats c
        JOIN chat_members cm ON cm.chat_id = c.id
        WHERE cm.user_id = :user_id
        ORDER BY c.created_at DESC
        """
    )
    result = await db.execute(q, {"user_id": user_id})
    rows = result.mappings().all()
    return [dict(r) for r in rows]


async def get_chat_by_id(db: AsyncSession, chat_id: str) -> Optional[dict]:
    q = text(
        """
        SELECT id, created_at, type, title
        FROM chats
        WHERE id = :chat_id
        """
    )
    result = await db.execute(q, {"chat_id": chat_id})
    row = result.mappings().first()
    return dict(row) if row else None


async def create_chat(db: AsyncSession, type_: str, title: Optional[str] = None) -> dict:
    q = text(
        """
        INSERT INTO chats (type, title)
        VALUES (:type, :title)
        RETURNING id, created_at, type, title
        """
    )
    result = await db.execute(q, {"type": type_, "title": title})
    await db.commit()
    row = result.mappings().first()
    return dict(row)


async def add_chat_member(db: AsyncSession, chat_id: str, user_id: str, role: str = "member") -> None:
    q = text(
        """
        INSERT INTO chat_members (chat_id, user_id, role)
        VALUES (:chat_id, :user_id, :role)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET role = EXCLUDED.role
        """
    )
    await db.execute(q, {"chat_id": chat_id, "user_id": user_id, "role": role})
    await db.commit()


async def get_messages_for_chat(db: AsyncSession, chat_id: str, limit: int = 100, offset: int = 0) -> List[dict]:
    q = text(
        """
        SELECT id, created_at, updated_at, chat_id, sender_id, text, replies_to
        FROM messages
        WHERE chat_id = :chat_id
        ORDER BY created_at ASC
        OFFSET :offset LIMIT :limit
        """
    )
    result = await db.execute(q, {"chat_id": chat_id, "limit": limit, "offset": offset})
    rows = result.mappings().all()
    return [dict(r) for r in rows]


async def create_message(db: AsyncSession, chat_id: str, text_: str, sender_id: Optional[str] = None, replies_to: Optional[str] = None) -> dict:
    q = text(
        """
        INSERT INTO messages (chat_id, sender_id, text, replies_to)
        VALUES (:chat_id, :sender_id, :text, :replies_to)
        RETURNING id, created_at, updated_at, chat_id, sender_id, text, replies_to
        """
    )
    result = await db.execute(q, {"chat_id": chat_id, "sender_id": sender_id, "text": text_, "replies_to": replies_to})
    await db.commit()
    row = result.mappings().first()
    return dict(row)