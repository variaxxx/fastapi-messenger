import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    ALLOWED_ORIGINS: list[str] = ["http://127.0.0.1:4200", "http://localhost:4200"]


settings = Settings()
