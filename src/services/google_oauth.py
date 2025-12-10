import re

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import src.queries.blacklisted_token_queries as token_queries
import src.queries.user_queries as user_queries
from src.core.config import settings
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt,
)
from src.schemas.auth import TokenPayload, TokensResponse
from src.schemas.user import CreateUser


async def google_login(db: AsyncSession, code: str) -> TokensResponse:
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            },
        )
        token = token_res.json().get("access_token")

        userinfo_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
        userinfo = userinfo_res.json()

    google_id = userinfo.get("id")
    email = userinfo.get("email")
    name = userinfo.get("name") or "user"

    if not email or not google_id:
        raise HTTPException(400, "Bad request")

    user = await user_queries.get_by_google_id(db, google_id)

    if not user:
        username = _generate_username(name, email)
        create_user = CreateUser(
            username=username, email=email, google_id=google_id
        )
        user = await user_queries.create(db, create_user)

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))

    return {"access_token": access, "refresh_token": refresh}


async def refresh(db: AsyncSession, refresh_token: str) -> TokensResponse:
    payload: TokenPayload = decode_jwt(refresh_token, is_refresh_token=True)
    user_id = payload.get("user").get("id")

    if await token_queries.is_blacklisted(db, refresh_token):
        raise HTTPException(401, "Invalid token")

    user = await user_queries.get_by_id(db, user_id)
    if not user:
        raise HTTPException(401, "Invalid token")

    await token_queries.blacklist(db, refresh_token, user_id)

    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)

    return {"access_token": new_access, "refresh_token": new_refresh}


async def logout(db: AsyncSession, refresh_token: str):
    payload: TokenPayload = decode_jwt(refresh_token, is_refresh_token=True)
    await token_queries.blacklist(
        db, refresh_token, payload.get("user").get("id")
    )


def _generate_username(name: str, email: str):
    base = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_")
    return base or email.split("@")[0]
