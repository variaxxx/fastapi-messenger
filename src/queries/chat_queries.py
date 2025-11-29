from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.chat import (
    ChatInfo,
    ChatInfoDto,
    ChatMemberDto,
    MessageInfoDto,
)


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
        SELECT
            id, created_at, updated_at, chat_id,
            sender_id, text, is_edited, replies_to
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
                sender_id, text, is_edited, replies_to;
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


async def rename_chat(
    db: AsyncSession, editor_id: str, chat_id: str, title: str
) -> ChatInfoDto:
    q = text("""
        WITH updated_chat AS (
            UPDATE chats
            SET
                title = :title,
                updated_at = NOW()
            WHERE id = :chat_id AND type = 'group'
            RETURNING id, type, title
        ),
        last_message AS (
            SELECT *
            FROM messages
            WHERE chat_id = :chat_id
            ORDER BY created_at DESC
            LIMIT 1
        ),
        chat_member AS (
            SELECT
                role
            FROM chat_members
            WHERE chat_id = :chat_id AND user_id = :editor_id
            LIMIT 1
        )
        SELECT
            uc.*,
            cm.role,
            lm.id AS last_message_id,
            lm.text AS last_message_text,
            lm.created_at AS last_message_date,
            lm.sender_id AS last_message_sender
        FROM updated_chat uc
            JOIN chat_member AS cm ON TRUE
            LEFT JOIN last_message AS lm ON TRUE;
    """)
    result = await db.execute(
        q, {"chat_id": chat_id, "title": title, "editor_id": editor_id}
    )

    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "Chat not found")

    return ChatInfoDto.model_validate(row)


async def update_message(
    db: AsyncSession, message_id: str, user_id: str, text_: str
) -> MessageInfoDto:
    q = text("""
        UPDATE messages
        SET
            text = :text,
            updated_at = NOW(),
            is_edited = TRUE
        WHERE id = :id AND sender_id = :user_id
        RETURNING
            id, created_at, updated_at,
            chat_id, sender_id, text, is_edited, replies_to;
    """)
    result = await db.execute(
        q, {"id": message_id, "user_id": user_id, "text": text_}
    )
    row = result.mappings().first()

    if not row:
        raise HTTPException(404, "сообщение не найдено")

    return MessageInfoDto.model_validate(row)


async def get_chat_members(
    db: AsyncSession, chat_id: str, limit: int, offset: int
):
    q = text("""
        WITH total_count AS (
            SELECT COUNT(*) as total
            FROM chat_members
            WHERE chat_id = :chat_id
        ),
        paged AS (
        SELECT
                cm.user_id::text AS id,
                cm.role,
                u.displayed_name,
                u.avatar_url
            FROM chat_members cm
                JOIN users u ON u.id = cm.user_id
            WHERE cm.chat_id = :chat_id
            ORDER BY cm.user_id
            OFFSET :offset
            LIMIT :limit
        )
        SELECT
            p.*,
            tc.total
        FROM paged p
            RIGHT JOIN total_count tc ON TRUE;
    """)
    result = await db.execute(
        q, {"chat_id": chat_id, "offset": offset, "limit": limit}
    )
    rows = result.mappings().all()
    return [
        [
            ChatMemberDto.model_validate(row)
            for row in rows
            if row["id"] is not None
        ],
        rows[0].total,
    ]


async def remove_chat_member(
    db: AsyncSession, chat_id: str, user_id: str
) -> None:
    q = text("""
        DELETE FROM chat_members
        WHERE chat_id = :chat_id AND user_id = :user_id;
    """)
    await db.execute(q, {"chat_id": chat_id, "user_id": user_id})
