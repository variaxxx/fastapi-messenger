from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def count_chats_for_user(db: AsyncSession, user_id: str) -> int:
    q = text("""
        SELECT COUNT(DISTINCT c.id) AS total
        FROM chats c
        JOIN chat_members cm ON cm.chat_id = c.id
        WHERE cm.user_id = :user_id
    """)
    res = await db.execute(q, {"user_id": user_id})
    row = res.mappings().first()
    return int(row["total"]) if row and row["total"] is not None else 0


async def get_chats_for_user_paginated(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    order: str = "DESC",  # 'ASC' или 'DESC'
) -> List[dict]:
    """
    Возвращает список чатов для user_id с полями:
    id, title, type, last_message_text, last_message_created_at, participants_count
    Сортировка по времени последнего сообщения
    """
    if order.upper() not in ("ASC", "DESC"):
        order = "DESC"
    order = order.upper()

    # LATERAL для получения последнего сообщения для каждого чата
    # и подзапрос для подсчета участников.
    q = text(f"""
        SELECT
            c.id::text AS id,
            c.title,
            c.type,
            lm.text AS last_message_text,
            lm.created_at AS last_message_created_at,
            COALESCE(pm.participants_count, 0) AS participants_count
        FROM chats c
        JOIN chat_members cm ON cm.chat_id = c.id
        LEFT JOIN LATERAL (
            SELECT m.text, m.created_at
            FROM messages m
            WHERE m.chat_id = c.id
            ORDER BY m.created_at DESC
            LIMIT 1
        ) lm ON TRUE
        LEFT JOIN (
            SELECT chat_id, COUNT(*) AS participants_count
            FROM chat_members
            GROUP BY chat_id
        ) pm ON pm.chat_id = c.id
        WHERE cm.user_id = :user_id
        GROUP BY c.id, c.title, c.type, lm.text, lm.created_at, pm.participants_count
        ORDER BY lm.created_at {order} NULLS LAST
        OFFSET :offset
        LIMIT :limit
    """)

    params = {"user_id": user_id, "limit": limit, "offset": offset}
    res = await db.execute(q, params)
    rows = res.mappings().all()
    # mappings().all() — возвращает list[RowMapping]; конвертируем в dict
    return [dict(r) for r in rows]


# Reuse: get_chat_by_id (simple)
async def get_chat_by_id(db: AsyncSession, chat_id: str) -> Optional[dict]:
    q = text("""
        SELECT id::text AS id, created_at, type, title
        FROM chats
        WHERE id = :chat_id
    """)
    res = await db.execute(q, {"chat_id": chat_id})
    row = res.mappings().first()
    return dict(row) if row else None


# Messages queries (basic)
async def get_messages_for_chat(db: AsyncSession, chat_id: str, limit: int = 100, offset: int = 0) -> List[dict]:
    q = text("""
        SELECT id::text AS id, created_at, updated_at, chat_id::text AS chat_id, sender_id::text AS sender_id, text, replies_to::text AS replies_to
        FROM messages
        WHERE chat_id = :chat_id
        ORDER BY created_at ASC
        OFFSET :offset LIMIT :limit
    """)
    res = await db.execute(q, {"chat_id": chat_id, "limit": limit, "offset": offset})
    rows = res.mappings().all()
    return [dict(r) for r in rows]


async def create_chat(db: AsyncSession, type_: str, title: Optional[str] = None) -> dict:
    q = text("""
        INSERT INTO chats (type, title)
        VALUES (:type, :title)
        RETURNING id::text AS id, created_at, type, title
    """)
    res = await db.execute(q, {"type": type_, "title": title})
    await db.commit()
    row = res.mappings().first()
    return dict(row)


async def add_chat_member(db: AsyncSession, chat_id: str, user_id: str, role: str = "member"):
    q = text("""
        INSERT INTO chat_members (chat_id, user_id, role)
        VALUES (:chat_id, :user_id, :role)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET role = EXCLUDED.role
    """)
    await db.execute(q, {"chat_id": chat_id, "user_id": user_id, "role": role})
    await db.commit()


async def create_message(db: AsyncSession, chat_id: str, text_: str, sender_id: Optional[str] = None, replies_to: Optional[str] = None) -> dict:
    q = text("""
        INSERT INTO messages (chat_id, sender_id, text, replies_to)
        VALUES (:chat_id, :sender_id, :text, :replies_to)
        RETURNING id::text AS id, created_at, updated_at, chat_id::text AS chat_id, sender_id::text AS sender_id, text, replies_to::text AS replies_to
    """)
    res = await db.execute(q, {"chat_id": chat_id, "sender_id": sender_id, "text": text_, "replies_to": replies_to})
    await db.commit()
    row = res.mappings().first()
    return dict(row)