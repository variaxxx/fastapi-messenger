from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.blacklisted_token import BlacklistedToken


class TokenBlacklistQueries:

    @staticmethod
    async def is_blacklisted(session: AsyncSession, jti: str) -> bool:
        res = await session.execute(select(BlacklistedToken).where(BlacklistedToken.jti == jti))
        return res.scalars().first() is not None

    @staticmethod
    async def blacklist(session: AsyncSession, jti: str, exp_datetime):
        token = BlacklistedToken(jti=jti, expired_at=exp_datetime)
        session.add(token)
        await session.flush()
