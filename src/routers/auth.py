from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

from app.schemas.auth import TokenPair, GoogleLoginRequest
from app.schemas.user import UserOut

from app.services.auth_service import AuthService
from app.core.security import decode_jwt
from app.queries.user_queries import UserQueries


router = APIRouter(prefix="/auth", tags=["Auth"])


async def get_current_user(
    authorization: str = Header(...),
    session: AsyncSession = Depends(get_db)
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")

    token = authorization.split()[1]
    payload = decode_jwt(token)

    if payload["type"] != "access":
        raise HTTPException(401, "Not access token")

    user = await UserQueries.get_by_id(session, int(payload["sub"]))
    if not user:
        raise HTTPException(401, "User not found")

    return user


@router.post("/google", response_model=dict)
async def google_login(
    body: GoogleLoginRequest,
    session: AsyncSession = Depends(get_db)
):
    return await AuthService.google_login(session, body.oauth_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    refresh_token: str,
    session: AsyncSession = Depends(get_db)
):
    return await AuthService.refresh(session, refresh_token)


@router.post("/logout")
async def logout(
    refresh_token: str,
    session: AsyncSession = Depends(get_db)
):
    return await AuthService.logout(session, refresh_token)


@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return user
