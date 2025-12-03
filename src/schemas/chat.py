from datetime import datetime
from typing import List, Optional

from pydantic import UUID4, BaseModel, Field


class ChatInfo(BaseModel):
    id: UUID4
    created_at: datetime
    type: str = Field(..., pattern="^(direct|group)$")
    title: str
    avatar_url: str | None


class ChatInfoDto(BaseModel):
    id: UUID4
    type: str = Field(..., pattern="^(direct|group)$")
    title: str | None
    avatar_url: str | None
    role: str = Field(..., pattern="^(member|admin)$")
    last_message_id: UUID4 | None
    last_message_text: str | None
    last_message_date: datetime | None
    last_message_sender: UUID4 | None


class ShortChatInfoDto(BaseModel):
    id: UUID4
    type: str = Field(..., pattern="^(direct|group)$")
    title: str | None
    avatar_url: str | None


class CreateChatDto(BaseModel):
    type: str = Field(..., pattern="^(direct|group)$")
    title: Optional[str] = None
    members: List[UUID4] = Field(default_factory=list)


class SendMessageDto(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    replies_to: Optional[UUID4] = None


class MessageInfoDto(BaseModel):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    chat_id: UUID4
    sender_id: UUID4
    text: str
    is_edited: bool
    replies_to: Optional[UUID4]


class RenameChatDto(BaseModel):
    new_title: str


class EditMessageDto(BaseModel):
    text: str


class ChatMemberDto(BaseModel):
    id: str
    displayed_name: str | None
    avatar_url: str | None
    role: str = Field(..., pattern="^(member|admin)$")


class InviteChatMembersDto(BaseModel):
    members: List[UUID4] = Field(default_factory=list)
