from fastapi import HTTPException
from sqlalchemy import Result, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.user import CreateUser, UserInfo


async def get_by_id(db: AsyncSession, user_id: str) -> UserInfo | None:
    res: Result = await db.execute(
        text("""
            SELECT *
            FROM users u
            WHERE u.id = :user_id;
        """),
        {"user_id": user_id},
    )
    row = res.mappings().first()
    if not row:
        return None
    return UserInfo.model_validate(row)


async def get_by_google_id(db: AsyncSession, google_id: str) -> UserInfo | None:
    res: Result = await db.execute(
        text("""
            SELECT *
            FROM users u
            WHERE u.google_id = :google_id;
        """),
        {"google_id": google_id},
    )

    row = res.mappings().first()
    if not row:
        return None

    return UserInfo.model_validate(row)


async def get_by_email(db: AsyncSession, email: str) -> UserInfo | None:
    res: Result = await db.execute(
        text("""
            SELECT *
            FROM users u
            WHERE u.email = :email;
        """),
        {"email": email},
    )

    row = res.mappings().first()
    if not row:
        return None

    return UserInfo.model_validate(row)


async def create(db: AsyncSession, user: CreateUser) -> UserInfo | None:
    try:
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
        row = res.mappings().first()
        if not row:
            return None
        return UserInfo.model_validate(row)
    except IntegrityError as e:
        if getattr(e.orig, "pgcode", None) == "23505":
            raise HTTPException(
                409, "User with this credentials already exists"
            )
        raise


async def change_username(
    db: AsyncSession, user_id: str, username: str
) -> UserInfo | None:
    try:
        res: Result = await db.execute(
            text("""
                UPDATE users
                SET
                    username = :username,
                    updated_at = NOW()
                WHERE id = :user_id
                RETURNING *;
            """),
            {"username": username, "user_id": user_id},
        )

        row = res.mappings().first()
        if not row:
            return None

        return UserInfo.model_validate(row)
    except IntegrityError as e:
        if getattr(e.orig, "pgcode", None) == "23505":
            raise HTTPException(409, "Username is already taken")
        raise


async def find_by_username(db: AsyncSession, username: str) -> UserInfo | None:
    res: Result = await db.execute(
        text("""
            SELECT *
            FROM users
            WHERE username = :username;
        """),
        {"username": username},
    )

    row = res.mappings().first()
    if not row:
        return None

    return UserInfo.model_validate(row)


async def find_by_id(db: AsyncSession, id: str) -> UserInfo | None:
    res: Result = await db.execute(
        text("""
            SELECT *
            FROM users
            WHERE id = :id;
        """),
        {"id": id},
    )

    row = res.mappings().first()
    if not row:
        return None

    return UserInfo.model_validate(row)


async def change_avatar(
    db: AsyncSession, user_id: str, url: str
) -> UserInfo | None:
    res: Result = await db.execute(
        text("""
            UPDATE users
            SET
                avatar_url = :url,
                updated_at = NOW()
            WHERE id = :user_id
            RETURNING *;
        """),
        {"url": url, "user_id": user_id},
    )

    row = res.mappings().first()
    if not row:
        return None

    return UserInfo.model_validate(row)


async def change_displayed_name(
    db: AsyncSession, user_id: str, name: str
) -> UserInfo | None:
    res: Result = await db.execute(
        text("""
            UPDATE users
            SET
                displayed_name = :name,
                updated_at = NOW()
            WHERE id = :user_id
            RETURNING *;
        """),
        {"name": name, "user_id": user_id},
    )

    row = res.mappings().first()
    if not row:
        return None

    return UserInfo.model_validate(row)


async def edit_bio(db: AsyncSession, user_id: str, bio: str) -> UserInfo | None:
    res: Result = await db.execute(
        text("""
            UPDATE users
            SET
                bio = :bio,
                updated_at = NOW()
            WHERE id = :user_id
            RETURNING *;
        """),
        {"bio": bio, "user_id": user_id},
    )

    row = res.mappings().first()
    if not row:
        return None

    return UserInfo.model_validate(row)


async def username_exists(db: AsyncSession, username: str) -> bool:
    res: Result = await db.execute(
        text("""
            SELECT 1
            FROM users
            WHERE username = :user
            LIMIT 1
        """),
        {"user": username},
    )
    return res.scalar() is not None
