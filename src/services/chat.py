import os
from typing import List
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

import src.queries.chat_queries as chat_queries
from src.core.config import settings
from src.db.minio import remove_from_minio, upload_to_minio
from src.schemas.chat import (
    ChatInfo,
    ChatInfoDto,
    ChatMemberDto,
    CreateChatDto,
    MessageInfoDto,
    SendMessageDto,
)
from src.services.image import resize_image


def validate_chat_title(title: str) -> bool:
    title = title.strip()
    if not 1 <= len(title) <= 100:
        return False
    return True


async def get_chats_for_user(
    db: AsyncSession, user_id: str, limit: int = 20, offset: int = 0
) -> List[ChatInfoDto]:
    return await chat_queries.get_chats_for_user(
        db, user_id=user_id, limit=limit, offset=offset
    )


async def create_chat(
    db: AsyncSession, payload: CreateChatDto, creator_id: str
) -> dict:
    if payload.type == "group" and not payload.title:
        raise HTTPException(400, "Title is required for groups")
    title = payload.title.strip()
    if payload.type == "group" and not validate_chat_title(title):
        raise HTTPException(403, "Invalid chat title")

    if (
        payload.type == "direct"
        and len([member for member in payload.members if member != creator_id])
        != 1
    ):
        raise HTTPException(400, "One member must be provided for direct chats")

    chat: ChatInfo = await chat_queries.create_chat(
        db,
        type_=payload.type,
        title=(title if payload.type != "direct" else None),
    )

    await chat_queries.add_chat_member(
        db,
        chat_id=chat.id,
        user_id=creator_id,
        role=("admin" if payload.type == "group" else "member"),
    )
    await chat_queries.add_chat_members(
        db, chat_id=chat.id, user_ids=payload.members
    )
    return chat


async def get_messages(
    db: AsyncSession, chat_id: str, limit: int = 100, offset: int = 0
) -> List[MessageInfoDto]:
    return await chat_queries.get_messages_for_chat(
        db, chat_id=chat_id, limit=limit, offset=offset
    )


async def send_message(
    db: AsyncSession,
    chat_id: str,
    payload: SendMessageDto,
    sender_id: str,
) -> MessageInfoDto:
    return await chat_queries.send_message(
        db,
        chat_id=chat_id,
        text_=payload.text,
        sender_id=sender_id,
        replies_to=payload.replies_to,
    )


async def is_user_in_chat(db: AsyncSession, chat_id: str, user_id) -> bool:
    return await chat_queries.is_user_in_chat(
        db=db, chat_id=chat_id, user_id=user_id
    )


async def get_chats_total(db: AsyncSession, user_id: str) -> int:
    return await chat_queries.get_chats_total(db=db, user_id=user_id)


async def get_messages_total(db: AsyncSession, chat_id: str) -> int:
    return await chat_queries.get_messages_total(db=db, chat_id=chat_id)


async def rename_chat(
    db: AsyncSession, editor_id: str, chat_id: str, title: str
) -> ChatInfoDto:
    title = title.strip()
    if not validate_chat_title(title):
        raise HTTPException(403, "Invalid chat title")

    return await chat_queries.rename_chat(
        db, chat_id=chat_id, editor_id=editor_id, title=title
    )


async def edit_message(
    db: AsyncSession, message_id: str, user_id: str, text: str
) -> MessageInfoDto:
    return await chat_queries.update_message(
        db, message_id=message_id, user_id=user_id, text_=text
    )


async def list_members(
    db: AsyncSession, chat_id: str, limit: int = 1000, offset: int = 0
) -> List[ChatMemberDto]:
    return await chat_queries.get_chat_members(
        db, chat_id, limit=limit, offset=offset
    )


async def delete_member(
    db: AsyncSession, chat_id: str, target_user_id: str
) -> None:
    [deleted, new_admin_id] = await chat_queries.remove_chat_member(
        db, chat_id=chat_id, user_id=target_user_id
    )
    if not deleted:
        raise HTTPException(400, "User is not a member of this chat")


async def leave_chat(db: AsyncSession, chat_id: str, user_id: str) -> None:
    [deleted, new_admin_id] = await chat_queries.remove_chat_member(
        db, chat_id=chat_id, user_id=user_id
    )
    if not deleted:
        raise HTTPException(400, "You are not a member of this chat")


async def delete_message(
    db: AsyncSession, message_id: str, user_id: str
) -> None:
    return await chat_queries.delete_message(
        db, message_id=message_id, user_id=user_id
    )


async def invite_members(db: AsyncSession, members: List[str], chat_id: str):
    members = await chat_queries.add_chat_members(
        db, chat_id=chat_id, user_ids=members
    )

    if not members:
        raise HTTPException(400, "No valid user IDs provided")
    return members


async def is_user_chat_admin(
    db: AsyncSession, chat_id: str, user_id: str
) -> bool:
    [members, total] = await list_members(db, chat_id=str(chat_id))
    me = [member for member in members if member.id == user_id]
    if not me or me[0].role != "admin":
        return False
    return True


async def change_group_picture(
    db: AsyncSession, chat_id: str, file: UploadFile, user_id: str
):
    allowed_types = {"image/png", "image/jpeg", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Unsupported file type")

    old_chat_info: ChatInfo = await chat_queries.get_chat_by_id(
        db, chat_id=chat_id, user_id=user_id
    )

    if not old_chat_info or old_chat_info.type != "group":
        raise HTTPException(404, "Group not found")

    if old_chat_info.avatar_url:
        remove_from_minio(
            old_chat_info.avatar_url.split("/")[-1],
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
    return await chat_queries.change_group_picture(
        db=db, chat_id=chat_id, avatar_url=avatar_url
    )
