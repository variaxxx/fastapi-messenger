from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel


class TokenUserInfo(BaseModel):
    id: str


class TokenPayload(TypedDict):
    user: TokenUserInfo
    iat: datetime
    exp: datetime


class TokensResponse(BaseModel):
    access_token: str
    refresh_token: str


class GoogleLoginDto(BaseModel):
    oauth_token: str
