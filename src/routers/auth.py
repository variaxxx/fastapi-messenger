from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import src.services.google_oauth as auth_service
from src.dependencies import extract_bearer_token, get_async_session
from src.response import ResponseStructure
from src.schemas.auth import TokensResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/google", response_model=ResponseStructure[TokensResponse])
async def google_login(
    code: str, db: AsyncSession = Depends(get_async_session)
) -> TokensResponse:
    return await auth_service.google_login(db, code)


@router.post("/refresh", response_model=ResponseStructure[TokensResponse])
async def refresh(
    token: Annotated[str, Depends(extract_bearer_token)],
    session: AsyncSession = Depends(get_async_session),
) -> TokensResponse:
    return await auth_service.refresh(session, token)


@router.post("/logout", status_code=204, response_model=None)
async def logout(
    token: Annotated[str, Depends(extract_bearer_token)],
    session: AsyncSession = Depends(get_async_session),
):
    return await auth_service.logout(session, token)


# @router.get("/me")
# def me(user: Annotated[TokenPayload, Depends(auth_guard)]):
#     return "me"
