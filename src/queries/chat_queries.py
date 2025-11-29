from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.chat import ChatInfo, ChatInfoDto, MessageInfoDto


async def get_chats_for_user(
    db: AsyncSession, user_id: str, limit: int, offset: int
) -> List[ChatInfoDto]:
    q = text(
        """
        SELECT
            c.id,
            c.created_at,
            c.type,

            CASE
                WHEN c.type = 'direct' THEN other_user.name
                ELSE c.title
            END AS title,

            cm.role,
            m.id AS last_message_id,
            m.text AS last_message_text,
            m.created_at AS last_message_date,
            m.sender_id AS last_message_sender
        FROM chats c
            JOIN chat_members cm ON cm.chat_id = c.id

            LEFT JOIN LATERAL (
                SELECT COALESCE(u.displayed_name, 'Аноним') AS name
                FROM chat_members AS cm2
                JOIN users AS u ON u.id = cm2.user_id
                WHERE cm2.chat_id = c.id
                    AND cm2.user_id <> :user_id
                LIMIT 1
            ) AS other_user ON TRUE

            LEFT JOIN LATERAL (
                SELECT *
                FROM messages
                WHERE messages.chat_id = c.id
                ORDER BY messages.created_at DESC
                LIMIT 1
            ) AS m ON TRUE
        WHERE cm.user_id = :user_id
        ORDER BY COALESCE(m.created_at, c.created_at) DESC
        OFFSET :offset
        LIMIT :limit;
        """
    )
    result = await db.execute(
        q, {"user_id": user_id, "offset": offset, "limit": limit}
    )
    rows = result.mappings().all()
    return [ChatInfoDto.model_validate(row) for row in rows]


async def get_chat_by_id(
    db: AsyncSession, chat_id: str, user_id: str
) -> Optional[ChatInfo]:
    q = text(
        """
        SELECT *
        FROM chats
            JOIN chat_members cm ON
                cm.chat_id = c.id
                AND cm.user_id = :user_id
        WHERE id = :chat_id;
        """
    )
    result = await db.execute(q, {"chat_id": chat_id, "user_id": user_id})
    row = result.mappings().first()
    return ChatInfo.model_validate(row)


async def create_chat(
    db: AsyncSession, type_: str, title: Optional[str] = None
) -> ChatInfo:
    q = text(
        """
        INSERT INTO chats (type, title)
        VALUES (:type, :title)
        RETURNING id, created_at, type, title;
        """
    )
    result = await db.execute(q, {"type": type_, "title": title})
    row = result.mappings().first()
    return ChatInfo.model_validate(row)


async def add_chat_member(
    db: AsyncSession, chat_id: str, user_id: str, role: str = "member"
) -> None:
    try:
        q = text(
            """
            INSERT INTO chat_members (chat_id, user_id, role)
            VALUES (:chat_id, :user_id, :role)
            ON CONFLICT (chat_id, user_id) DO UPDATE SET role = EXCLUDED.role;
            """
        )
        await db.execute(
            q, {"chat_id": chat_id, "user_id": user_id, "role": role}
        )
    except IntegrityError as e:
        await db.rollback()

        if getattr(e.orig, "pgcode", None) == "23505":
            raise HTTPException(404, "Chat or user not found")
        raise


async def get_messages_for_chat(
    db: AsyncSession, chat_id: str, limit: int = 100, offset: int = 0
) -> List[MessageInfoDto]:
    q = text(
        """
        SELECT id, created_at, updated_at, chat_id, sender_id, text, replies_to
        FROM messages
        WHERE chat_id = :chat_id
        ORDER BY created_at DESC
        OFFSET :offset
        LIMIT :limit;
        """
    )
    result = await db.execute(
        q, {"chat_id": chat_id, "limit": limit, "offset": offset}
    )
    rows = result.mappings().all()
    return [MessageInfoDto.model_validate(row) for row in rows]


async def send_message(
    db: AsyncSession,
    chat_id: str,
    text_: str,
    sender_id: str,
    replies_to: Optional[str] = None,
) -> MessageInfoDto:
    try:
        q = text(
            """
            INSERT INTO messages (chat_id, sender_id, text, replies_to)
            VALUES (:chat_id, :sender_id, :text, :replies_to)
            RETURNING
                id, created_at, updated_at, chat_id,
                sender_id, text, replies_to;
            """
        )
        result = await db.execute(
            q,
            {
                "chat_id": chat_id,
                "sender_id": sender_id,
                "text": text_,
                "replies_to": replies_to,
            },
        )
        row = result.mappings().first()
        return MessageInfoDto.model_validate(row)
    except IntegrityError as e:
        await db.rollback()

        if getattr(e.orig, "pgcode", None) == "23505":
            raise HTTPException(404, "Chat or user not found")
        raise


async def is_user_in_chat(db: AsyncSession, user_id: str, chat_id: str) -> bool:
    q = text(
        """
        SELECT 1
        FROM chat_members cm
        WHERE
            cm.user_id = :user_id
            AND cm.chat_id = :chat_id;
        """
    )
    result = await db.execute(q, {"user_id": user_id, "chat_id": chat_id})
    return result.scalar() is not None


async def get_chats_total(db: AsyncSession, user_id: str) -> int:
    q = text(
        """
        SELECT COUNT(*)
        FROM chat_members cm
        WHERE cm.user_id = :user_id;
        """
    )
    result = await db.execute(q, {"user_id": user_id})
    return result.scalar()


async def get_messages_total(db: AsyncSession, chat_id: str) -> int:
    q = text(
        """
        SELECT COUNT(*)
        FROM messages m
        WHERE m.chat_id = :chat_id;
        """
    )
    result = await db.execute(q, {"chat_id": chat_id})
    return result.scalar()
