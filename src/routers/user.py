from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

import src.services.user as user_service
from src.dependencies import auth_guard, get_async_session
from src.schemas.auth import TokenUserInfo
from src.schemas.user import (
    ChangeDisplayedNameDto,
    ChangeUsernameDto,
    EditBioDto,
    UserInfoDto,
    UsernameAvailabilityDto,
)

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/find-by-username/{username}", response_model=UserInfoDto)
async def find_by_username(
    username: str,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserInfoDto:
    return await user_service.find_by_username(db, username)


@router.get("/check-username", response_model=UsernameAvailabilityDto)
async def check_username(
    username: str,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> UsernameAvailabilityDto:
    exists = await user_service.username_exists(db, username)

    return {"available": not exists, "reason": None if not exists else "taken"}


@router.get("/me", response_model=UserInfoDto)
async def get_me(
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserInfoDto:
    return await user_service.find_by_id(db, user.id)


@router.get("/{id}", response_model=UserInfoDto)
async def find_by_id(
    id: str,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserInfoDto:
    return await user_service.find_by_id(db, id)


@router.patch("/me/username", response_model=UserInfoDto)
async def change_username(
    body: ChangeUsernameDto,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserInfoDto:
    return await user_service.change_username(db, user.id, body.new_username)


@router.patch("/me/avatar", response_model=UserInfoDto)
async def change_avatar(
    file: Annotated[UploadFile, File(...)],
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserInfoDto:
    return await user_service.change_avatar(db, user.id, file)


@router.patch("/me/name", response_model=UserInfoDto)
async def change_displayed_name(
    body: ChangeDisplayedNameDto,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserInfoDto:
    return await user_service.change_displayed_name(db, user.id, body.new_name)


@router.patch("/me/bio", response_model=UserInfoDto)
async def edit_bio(
    body: EditBioDto,
    user: Annotated[TokenUserInfo, Depends(auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserInfoDto:
    return await user_service.edit_bio(db, user.id, body.bio)
