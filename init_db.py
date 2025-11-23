import asyncio

from sqlalchemy import text

from src.db.database import engine


async def init():
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(100) UNIQUE NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                displayed_name VARCHAR(50) NOT NULL,
                avatar_url VARCHAR(200),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        )

        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS blacklisted_refresh_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                token TEXT UNIQUE,
                user_id UUID REFERENCES users(id)
            );
        """)
        )

        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS chats (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                type TEXT NOT NULL CHECK (type IN ('direct', 'group')),
                title VARCHAR(255)
            );
        """)
        )

        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                chat_id UUID REFERENCES chats(id),
                sender_id UUID REFERENCES users(id),
                text TEXT NOT NULL,
                replies_to UUID REFERENCES messages(id) ON DELETE SET NULL
            );
        """)
        )

        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS chat_members (
                chat_id UUID REFERENCES chats(id),
                user_id UUID REFERENCES users(id),
                role TEXT NOT NULL CHECK (role IN ('member', 'admin')),
                PRIMARY KEY(chat_id, user_id)
            );
        """)
        )

        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS attachments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
                url VARCHAR(500) NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('photo', 'video', 'document')),
                size_bytes INT NOT NULL CHECK (size_bytes > 0),
                filename VARCHAR(255) NOT NULL
            );
        """)
        )


asyncio.run(init())
