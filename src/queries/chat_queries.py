from typing import List, Optional, Tuple

from fastapi import HTTPException
from pydantic import UUID4
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.chat import (
    AttachmentInfoDto,
    ChatInfo,
    ChatInfoDto,
    ChatMemberDto,
    MessageInfo,
    MessageInfoDto,
    ShortChatInfoDto,
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
            c.avatar_url,

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
                WHERE messages.chat_id = c.id AND messages.is_deleted = FALSE
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


async def get_chat_by_id_short(
    db: AsyncSession, chat_id: str, user_id: Optional[str]
) -> Optional[ChatInfo]:
    q = text(
        f"""
        SELECT *
        FROM chats c
            JOIN chat_members cm ON
                cm.chat_id = c.id
                {"AND cm.user_id = :user_id" if user_id else ""}
        WHERE id = :chat_id;
        """
    )
    result = await db.execute(q, {"chat_id": chat_id, "user_id": user_id})
    row = result.mappings().first()

    if not row:
        return None

    return ChatInfo.model_validate(row)


async def get_chat_by_id(
    db: AsyncSession, chat_id: str, user_id: Optional[str]
) -> Optional[ChatInfoDto]:
    q = text(
        f"""
        SELECT
            c.id,
            c.created_at,
            c.type,
            c.avatar_url,

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
                WHERE messages.chat_id = c.id AND messages.is_deleted = FALSE
                ORDER BY messages.created_at DESC
                LIMIT 1
            ) AS m ON TRUE
        WHERE {"cm.user_id = :user_id" if user_id else ""}
            AND cm.chat_id = :chat_id
        LIMIT 1;
        """
    )
    result = await db.execute(q, {"chat_id": chat_id, "user_id": user_id})
    row = result.mappings().first()

    if not row:
        return None

    return ChatInfoDto.model_validate(row)


async def create_chat(
    db: AsyncSession,
    type_: str,
    title: Optional[str],
    creator_id: str,
    members: List[str],
) -> Tuple[ChatInfo, List[str]]:
    try:
        async with db.begin():
            q = text(
                """
                INSERT INTO chats (type, title)
                VALUES (:type, :title)
                RETURNING id, created_at, type, title, avatar_url;
                """
            )
            result = await db.execute(q, {"type": type_, "title": title})
            row = result.mappings().first()
            chat = ChatInfo.model_validate(row)

            q_member = text("""
                INSERT INTO chat_members (chat_id, user_id, role)
                VALUES (:chat_id, :user_id, :role)
                ON CONFLICT (chat_id, user_id) DO UPDATE SET role = EXCLUDED.role;
            """)
            result = await db.execute(
                q_member,
                {
                    "chat_id": chat.id,
                    "user_id": creator_id,
                    "role": "admin" if type_ == "group" else "member",
                },
            )

            q = text("""
                WITH valid_users AS (
                    SELECT id
                    FROM users
                    WHERE id = ANY(:user_ids)
                ),
                inserted AS (
                    INSERT INTO chat_members (chat_id, user_id, role)
                    SELECT :chat_id, id, 'member'
                    FROM valid_users
                    ON CONFLICT DO NOTHING
                    RETURNING user_id, role
                )
                SELECT u.id
                FROM inserted i
                    JOIN users u ON u.id = i.user_id;
            """)
            result = await db.execute(
                q, {"user_ids": members, "chat_id": chat.id}
            )
            rows = result.scalars().all()

            member_ids = [creator_id] + rows
            return [chat, member_ids]
    except IntegrityError as e:
        if getattr(e.orig, "pgcode", None) == "23503":
            raise HTTPException(404, "Chat or user not found")
        raise


async def get_messages_for_chat(
    db: AsyncSession, chat_id: str, limit: int = 100, offset: int = 0
) -> List[MessageInfoDto]:
    q = text(
        """
        SELECT
            m.id, m.created_at, m.updated_at, m.chat_id,
            m.sender_id, m.text, m.is_edited, m.replies_to,
            a.url AS a_url,
            a.type AS a_type,
            a.size_bytes AS a_size_bytes,
            a.filename AS a_filename
        FROM messages m
            LEFT JOIN attachments a ON a.message_id = m.id
        WHERE chat_id = :chat_id AND is_deleted = FALSE
        ORDER BY created_at DESC
        OFFSET :offset
        LIMIT :limit;
        """
    )
    result = await db.execute(
        q, {"chat_id": chat_id, "limit": limit, "offset": offset}
    )
    rows = result.mappings().all()

    messages_map = {}
    for row in rows:
        msg_id = row["id"]

        if msg_id not in messages_map:
            messages_map[msg_id] = {
                "id": row["id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "chat_id": row["chat_id"],
                "sender_id": row["sender_id"],
                "text": row["text"],
                "is_edited": row["is_edited"],
                "replies_to": row["replies_to"],
                "attachments": [],
            }

        if row["a_url"] is not None:
            messages_map[msg_id]["attachments"].append(
                AttachmentInfoDto(
                    message_id=row["id"],
                    url=row["a_url"],
                    type=row["a_type"],
                    size_bytes=row["a_size_bytes"],
                    filename=row["a_filename"],
                )
            )

    return [
        MessageInfoDto.model_validate(data) for data in messages_map.values()
    ]


async def send_message(
    db: AsyncSession,
    chat_id: str,
    text_: str,
    sender_id: str,
    replies_to: Optional[str] = None,
) -> MessageInfo:
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
        return MessageInfo.model_validate(row)
    except IntegrityError as e:
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
        WHERE m.chat_id = :chat_id AND is_deleted = FALSE;
        """
    )
    result = await db.execute(q, {"chat_id": chat_id})
    return result.scalar()


async def rename_chat(
    db: AsyncSession, editor_id: str, chat_id: str, title: str
) -> ShortChatInfoDto:
    q = text("""
        UPDATE chats
        SET
            title = :title,
            updated_at = NOW()
        WHERE id = :chat_id AND type = 'group'
        RETURNING id, type, title, avatar_url
    """)
    result = await db.execute(
        q, {"chat_id": chat_id, "title": title, "editor_id": editor_id}
    )

    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "Chat not found")

    return ShortChatInfoDto.model_validate(row)


async def update_message(
    db: AsyncSession, message_id: str, user_id: str, text_: str
) -> MessageInfo:
    q = text("""
        UPDATE messages
        SET
            text = :text,
            updated_at = NOW(),
            is_edited = TRUE
        WHERE id = :id AND sender_id = :user_id AND is_deleted = FALSE
        RETURNING
            id, created_at, updated_at,
            chat_id, sender_id, text, is_edited, replies_to;
    """)
    result = await db.execute(
        q, {"id": message_id, "user_id": user_id, "text": text_}
    )
    row = result.mappings().first()

    if not row:
        raise HTTPException(404, "Message not found")

    return MessageInfo.model_validate(row)


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
) -> Tuple[int, UUID4]:
    q = text("""
        WITH deleted_member AS (
            DELETE FROM chat_members
            WHERE chat_id = :chat_id AND user_id = :user_id
            RETURNING user_id, role
        ),
        was_admin AS (
            SELECT 1
            FROM deleted_member
            WHERE role = 'admin'
        ),
        new_admin AS (
            UPDATE chat_members
            SET role = 'admin'
            WHERE
                user_id = (
                    SELECT user_id
                    FROM chat_members
                    WHERE chat_id = :chat_id AND role <> 'admin'
                    ORDER BY random()
                    LIMIT 1
                )
                AND chat_id = :chat_id
                AND EXISTS (SELECT 1 FROM was_admin)
            RETURNING user_id
        )
        SELECT
            (SELECT COUNT(*) FROM deleted_member) AS deleted,
            (SELECT user_id FROM new_admin) AS new_admin_id;
    """)
    result = await db.execute(q, {"chat_id": chat_id, "user_id": user_id})
    return result.mappings().first()


async def delete_message(
    db: AsyncSession, message_id: str, user_id: str
) -> MessageInfo:
    q = text("""
        UPDATE messages m
        SET
            m.is_deleted = TRUE,
            m.updated_at = NOW()
        WHERE m.id = :message_id
            AND (
                m.sender_id = :user_id
                OR EXISTS (
                    SELECT 1
                    FROM chat_members cm
                    WHERE cm.user_id = :user_id
                        AND cm.chat_id = m.chat_id
                        AND cm.role = 'admin'
                )
        RETURNING m.id, m.created_at, m.updated_at, m.chat_id,
            m.sender_id, m.text, m.is_edited, m.replies_to;
    """)
    result = await db.execute(q, {"message_id": message_id, "user_id": user_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "Message not found")
    return MessageInfo.model_validate(row)


async def add_chat_members(
    db: AsyncSession, chat_id: str, user_ids: List[str]
) -> List[ChatMemberDto]:
    q = text("""
        WITH valid_users AS (
            SELECT id
            FROM users
            WHERE id = ANY(:user_ids)
        ),
        inserted AS (
            INSERT INTO chat_members (chat_id, user_id, role)
            SELECT :chat_id, id, 'member'
            FROM valid_users
            ON CONFLICT DO NOTHING
            RETURNING user_id, role
        )
        SELECT
            u.id::text,
            u.displayed_name,
            u.avatar_url,
            i.role
        FROM inserted i
            JOIN users u ON u.id = i.user_id;
    """)
    result = await db.execute(q, {"user_ids": user_ids, "chat_id": chat_id})
    rows = result.mappings().all()
    return [ChatMemberDto.model_validate(row) for row in rows]


async def change_group_picture(
    db: AsyncSession, chat_id: str, avatar_url: str
) -> Optional[ShortChatInfoDto]:
    q = text("""
        UPDATE chats
        SET avatar_url = :avatar_url
        WHERE type = 'group' AND id = :chat_id
        RETURNING id, type, title, avatar_url;
    """)
    result = await db.execute(q, {"avatar_url": avatar_url, "chat_id": chat_id})
    row = result.mappings().first()

    if not row:
        return None

    return ShortChatInfoDto.model_validate(row)


async def save_attachment(
    db: AsyncSession,
    message_id: str,
    file_url: str,
    type: str,
    size_bytes: int,
    filename: str,
) -> AttachmentInfoDto:
    q = text("""
        INSERT INTO attachments (message_id, url, type, size_bytes, filename)
        VALUES (:message_id, :file_url, :type, :size_bytes, :filename)
        RETURNING message_id, url, type, size_bytes, filename;
    """)
    result = await db.execute(
        q,
        {
            "message_id": message_id,
            "file_url": file_url,
            "type": type,
            "size_bytes": size_bytes,
            "filename": filename,
        },
    )
    row = result.mappings().first()
    return AttachmentInfoDto.model_validate(row)


async def get_all_chat_ids(db: AsyncSession, user_id: str) -> List[int]:
    q = text("""
        SELECT chat_id
        FROM chat_members
        WHERE user_id = :user_id;
    """)
    result = await db.execute(q, {"user_id": user_id})
    rows = result.mappings().all()
    return [row["chat_id"] for row in rows]


async def mark_message_read(
    db: AsyncSession, user_id: str, chat_id: str, message_id: str
) -> None:
    q = text("""
        UPDATE chat_members cm
        SET last_read_message_id = :message_id
        FROM messages m
        WHERE cm.chat_id = :chat_id
            AND cm.user_id = :user_id
            AND m.id = :message_id
            AND (
                cm.last_read_message_id IS NULL
                OR m.created_at > (
                    SELECT created_at
                    FROM messages
                    WHERE id = cm.last_read_message_id
                )
            );
    """)
    await db.execute(
        q, {"message_id": message_id, "chat_id": chat_id, "user_id": user_id}
    )
