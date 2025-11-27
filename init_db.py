import asyncio

from sqlalchemy import text

from src.db.database import engine


async def init():
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                google_id VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(32) UNIQUE NOT NULL,
                displayed_name VARCHAR(50),
                avatar_url VARCHAR(255),
                bio VARCHAR(255),
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
                type VARCHAR(16) NOT NULL CHECK (type IN ('direct', 'group')),
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
                text VARCHAR(1000) NOT NULL,
                replies_to UUID REFERENCES messages(id) ON DELETE SET NULL
            );
        """)
        )

        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS chat_members (
                chat_id UUID REFERENCES chats(id),
                user_id UUID REFERENCES users(id),
                role VARCHAR(16) NOT NULL CHECK (role IN ('member', 'admin')),
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
                type TEXT NOT NULL CHECK (
                    type IN ('photo', 'video', 'document')
                ),
                size_bytes INT NOT NULL CHECK (size_bytes > 0),
                filename VARCHAR(255) NOT NULL
            );
        """)
        )


asyncio.run(init())
