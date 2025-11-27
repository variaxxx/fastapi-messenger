import os
import re
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.minio import remove_from_minio, upload_to_minio
from src.queries import user_queries
from src.schemas.user import UserInfo, UserInfoDto
from src.services.image import resize_image


def _format_user_info(userinfo: UserInfo) -> UserInfoDto:
    return {
        "id": str(userinfo.id),
        "username": userinfo.username,
        "displayed_name": userinfo.displayed_name,
        "avatar_url": userinfo.avatar_url,
        "bio": userinfo.bio,
    }


def _validate_username(username: str) -> bool:
    if not 5 <= len(username) <= 32:
        return False
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False
    if username.startswith("_") or username.endswith("_"):
        return False
    return True


def _validate_displayed_name(name: str) -> bool:
    if not re.match(
        r"^(?!\s)(?!.*\s$)(?!.*\s{2,})[A-Za-zА-Яа-яЁё0-9 _-]{3,64}$", name
    ):
        return False
    return True


async def change_username(
    db: AsyncSession, user_id: str, new_username: str
) -> UserInfoDto:
    new_username = new_username.strip()
    if not _validate_username(new_username):
        raise HTTPException(400, "Invalid username")

    userinfo: UserInfo = await user_queries.change_username(
        db, user_id, new_username
    )

    if not userinfo:
        raise HTTPException(404, "User not found")

    return _format_user_info(userinfo)


async def find_by_username(db: AsyncSession, username: str) -> UserInfoDto:
    userinfo: UserInfo = await user_queries.find_by_username(db, username)

    if not userinfo:
        raise HTTPException(404, "User not found")

    return _format_user_info(userinfo)


async def find_by_id(db: AsyncSession, id: str) -> UserInfoDto:
    userinfo: UserInfo = await user_queries.find_by_id(db, id)

    if not userinfo:
        raise HTTPException(404, "User not found")

    return _format_user_info(userinfo)


async def change_avatar(
    db: AsyncSession, user_id: str, file: UploadFile
) -> UserInfoDto:
    allowed_types = {"image/png", "image/jpeg", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Unsupported file type")

    old_userinfo: UserInfo = await user_queries.find_by_id(db, user_id)

    if not old_userinfo:
        raise HTTPException(404, "User not found")

    if old_userinfo.avatar_url:
        remove_from_minio(
            old_userinfo["avatar_url"].split("/")[-1],
            settings.ASSETS_BUCKET_NAME,
        )

    filename = f"{uuid4().hex}{os.path.splitext(file.filename)[1]}"
    resized_image = resize_image(file)
    if not upload_to_minio(
        file=resized_image[0],
        bucket_name=settings.ASSETS_BUCKET_NAME,
        filename=filename,
    ):
        raise HTTPException(500, "Internal server error")

    avatar_url = f"/{settings.ASSETS_BUCKET_NAME}/{filename}"
    userinfo: UserInfo = await user_queries.change_avatar(
        db, user_id, avatar_url
    )

    return _format_user_info(userinfo)


async def change_displayed_name(
    db: AsyncSession, user_id: str, new_name: str
) -> UserInfoDto:
    if not _validate_displayed_name(new_name):
        raise HTTPException(400, "Invalid name")

    userinfo: UserInfo = await user_queries.change_displayed_name(
        db, user_id, new_name
    )

    if not userinfo:
        raise HTTPException(404, "User not found")

    return _format_user_info(userinfo)


async def edit_bio(db: AsyncSession, user_id: str, bio: str) -> UserInfoDto:
    bio = bio.strip()

    if not 0 < len(bio) <= 255:
        raise HTTPException(400, "Invalid bio")

    userinfo: UserInfo = await user_queries.edit_bio(db, user_id, bio)

    if not userinfo:
        raise HTTPException(404, "User not found")

    return _format_user_info(userinfo)


async def username_exists(db: AsyncSession, username: str) -> bool:
    username = username.strip()

    if not _validate_username(username):
        raise HTTPException(400, "Invalid username")

    return await user_queries.username_exists(db, username)
