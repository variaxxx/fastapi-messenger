from sqlalchemy import Result, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.user import CreateUser, UserInfo


async def get_by_id(db: AsyncSession, user_id: int) -> UserInfo:
    res: Result = await db.execute(
        text("""
        SELECT *
        FROM users u
        WHERE u.id = :user_id;
    """),
        {"user_id": user_id},
    )
    return res.mappings().first()


async def get_by_google_id(db: AsyncSession, google_id: str):
    res: Result = await db.execute(
        text("""
        SELECT *
        FROM users u
        WHERE u.google_id = :google_id;
    """),
        {"google_id": google_id},
    )
    return res.mappings().first()


async def get_by_email(db: AsyncSession, email: str):
    res: Result = await db.execute(
        text("""
        SELECT *
        FROM user u
        WHERE u.email = :email;
    """),
        {"email": email},
    )
    return res.mappings().first()


async def create(db: AsyncSession, user: CreateUser) -> UserInfo:
    res: Result = await db.execute(
        text("""
        INSERT INTO users (email, username, google_id)
        VALUES (:email, :username, :google_id)
        RETURNING *;
    """),
        {
            "email": user.email,
            "username": user.username,
            "google_id": user.google_id,
        },
    )
    return res.mappings().first()
