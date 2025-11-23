from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True, isolation_level="AUTOCOMMIT")
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
)
