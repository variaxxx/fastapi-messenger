from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User


class UserQueries:

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int):
        res = await session.execute(select(User).where(User.id == user_id))
        return res.scalars().first()

    @staticmethod
    async def get_by_google_id(session: AsyncSession, google_id: str):
        res = await session.execute(select(User).where(User.google_id == google_id))
        return res.scalars().first()

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str):
        res = await session.execute(select(User).where(User.email == email))
        return res.scalars().first()

    @staticmethod
    async def create(session: AsyncSession, user: User):
        session.add(user)
        await session.flush()
        return user
