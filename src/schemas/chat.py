from pydantic import BaseModel, Field, UUID4
from typing import Optional, List
from datetime import datetime


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


class ChatCreate(BaseModel):
    type: str = Field(..., regex="^(direct|group)$")
    title: Optional[str] = None
    members: Optional[List[UUID4]] = []


class ChatRead(BaseModel):
    id: UUID4
    created_at: datetime
    type: str
    title: Optional[str]

    class Config:
        orm_mode = True