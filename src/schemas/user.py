from datetime import datetime

from pydantic import UUID4, BaseModel


class CreateUser(BaseModel):
    email: str
    username: str
    google_id: str


class UserInfo(BaseModel):
    id: UUID4
    email: str
    username: str
    google_id: str
    displayed_name: str | None
    avatar_url: str | None
    bio: str | None
    created_at: datetime
    updated_at: datetime


class UserInfoDto(BaseModel):
    id: str
    username: str
    displayed_name: str | None
    avatar_url: str | None
    bio: str | None


class ChangeUsernameDto(BaseModel):
    new_username: str


class ChangeDisplayedNameDto(BaseModel):
    new_name: str


class EditBioDto(BaseModel):
    bio: str


class UsernameAvailabilityDto(BaseModel):
    available: bool
    reason: str | None
