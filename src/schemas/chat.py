from pydantic import BaseModel, Field, UUID4
from typing import Optional, List
from datetime import datetime


class ChatListItem(BaseModel):
    id: UUID4
    title: Optional[str]
    type: str
    last_message_text: Optional[str] = None
    last_message_created_at: Optional[datetime] = None
    participants_count: int = 0

    class Config:
        orm_mode = True


class ChatsListResponse(BaseModel):
    items: List[ChatListItem]
    total: int


class ChatCreate(BaseModel):
    type: str = Field(..., regex="^(direct|group)$")
    title: Optional[str] = None
    members: Optional[List[UUID4]] = []


class MessageCreate(BaseModel):
    sender_id: Optional[UUID4] = None
    text: str = Field(..., min_length=1, max_length=1000)
    replies_to: Optional[UUID4] = None


class MessageRead(BaseModel):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    chat_id: Optional[UUID4]
    sender_id: Optional[UUID4]
    text: str
    replies_to: Optional[UUID4]

    class Config:
        orm_mode = True
