import httpx
import re
from datetime import datetime

from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.queries.user_queries import UserQueries
from app.queries.token_blacklist_queries import TokenBlacklistQueries

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt,
)
from app.core.config import settings

from app.models.user import User


class AuthService:

    @staticmethod
    async def google_login(session: AsyncSession, oauth_token: str):
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"авторизация епт": f"Bearer {oauth_token}"}
            )

        if res.status_code != 200:
            raise HTTPException(400, "без авторизации сегодня")

        info = res.json()

        google_id = info.get("sub")
        email = info.get("email")
        name = info.get("name") or "user"

        if not email or not google_id:
            raise HTTPException(400, "гугл ид или емайа нет")

        user = await UserQueries.get_by_google_id(session, google_id)

        if not user:
            username = AuthService._generate_username(name, email)
            user = User(username=username, email=email, google_id=google_id)
            await UserQueries.create(session, user)

        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)

        return {
            "access_token": access,
            "refresh_token": refresh,
            "user": user
        }

    @staticmethod
    async def refresh(session: AsyncSession, refresh_token: str):
        payload = decode_jwt(refresh_token)

        if payload["type"] != "refresh":
            raise HTTPException(401, "No refresh token")

        jti = payload["jti"]
        exp = datetime.fromtimestamp(payload["exp"])

        if await TokenBlacklistQueries.is_blacklisted(session, jti):
            raise HTTPException(401, "Refresh token reused")

        user = await UserQueries.get_by_id(session, int(payload["sub"]))
        if not user:
            raise HTTPException(401, "User not found")

        await TokenBlacklistQueries.blacklist(session, jti, exp)

        new_access = create_access_token(user.id)
        new_refresh = create_refresh_token(user.id)

        return {"access_token": new_access, "refresh_token": new_refresh}

    @staticmethod
    async def logout(session: AsyncSession, refresh_token: str):
        payload = decode_jwt(refresh_token)

        if payload["type"] != "refresh":
            raise HTTPException(401, "Invalid refresh token")

        jti = payload["jti"]
        exp = datetime.fromtimestamp(payload["exp"])

        if not await TokenBlacklistQueries.is_blacklisted(session, jti):
            await TokenBlacklistQueries.blacklist(session, jti, exp)

        return True

    @staticmethod
    def _generate_username(name: str, email: str):
        base = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_")
        return base or email.split("@")[0]
