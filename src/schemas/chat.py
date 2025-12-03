from datetime import datetime
from typing import List, Optional

from pydantic import UUID4, BaseModel, Field


class AttachmentInfoDto(BaseModel):
    message_id: UUID4
    url: str
    type: str
    size_bytes: int
    filename: str


class ChatInfo(BaseModel):
    id: UUID4
    created_at: datetime
    type: str = Field(..., pattern="^(direct|group)$")
    title: str
    avatar_url: Optional[str]


class ChatInfoDto(BaseModel):
    id: UUID4
    type: str = Field(..., pattern="^(direct|group)$")
    title: Optional[str]
    avatar_url: Optional[str]
    role: str = Field(..., pattern="^(member|admin)$")
    last_message_id: Optional[UUID4]
    last_message_text: Optional[str]
    last_message_date: Optional[datetime]
    last_message_sender: Optional[UUID4]


class ShortChatInfoDto(BaseModel):
    id: UUID4
    type: str = Field(..., pattern="^(direct|group)$")
    title: Optional[str]
    avatar_url: Optional[str]


class CreateChatDto(BaseModel):
    type: str = Field(..., pattern="^(direct|group)$")
    title: Optional[str] = None
    members: List[UUID4] = Field(default_factory=list)


class MessageInfo(BaseModel):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    chat_id: UUID4
    sender_id: UUID4
    text: Optional[str]
    is_edited: bool
    replies_to: Optional[UUID4]


class MessageInfoDto(BaseModel):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    chat_id: UUID4
    sender_id: UUID4
    text: Optional[str]
    is_edited: bool
    replies_to: Optional[UUID4]
    attachments: List[AttachmentInfoDto]


class RenameChatDto(BaseModel):
    new_title: str


class EditMessageDto(BaseModel):
    text: str


class ChatMemberDto(BaseModel):
    id: str
    displayed_name: Optional[str]
    avatar_url: Optional[str]
    role: str = Field(..., pattern="^(member|admin)$")


class InviteChatMembersDto(BaseModel):
    members: List[UUID4] = Field(default_factory=list)
