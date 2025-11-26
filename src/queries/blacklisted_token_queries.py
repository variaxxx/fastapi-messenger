from sqlalchemy import Result, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def is_blacklisted(db: AsyncSession, token: str) -> bool:
    res: Result = await db.execute(
        text("""
        SELECT t.token
        FROM blacklisted_refresh_tokens t
        WHERE t.token = :token;
    """),
        {"token": token},
    )
    row = res.mappings().first()
    return row is not None


async def blacklist(db: AsyncSession, token: str, user_id: str):
    try:
        await db.execute(
            text("""
            INSERT INTO blacklisted_refresh_tokens (token, user_id)
            VALUES (:token, :user_id);
        """),
            {"token": token, "user_id": user_id},
        )
        return True
    except IntegrityError:
        await db.rollback()
