from datetime import datetime

from pydantic import BaseModel


class CreateUser(BaseModel):
    email: str
    username: str
    google_id: str


class UserInfo(BaseModel):
    id: str
    email: str
    username: str
    google_id: str
    displayed_name: str
    avatar_url: str
    created_at: datetime
    updated_at: datetime


class UserInfoDto(BaseModel):
    id: str
    username: str
    displayed_name: str
    avatar_url: str
