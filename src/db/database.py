from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, isolation_level="AUTOCOMMIT"
)
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
)
Base = declarative_base()
