from sqlalchemy import Column, String, DateTime
from app.db.database import Base


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    jti = Column(String, primary_key=True, index=True)
    expired_at = Column(DateTime, nullable=False)