from pydantic import BaseModel


class SendMessagePayload(BaseModel):
    chat_id: str
    text: str
    replies_to: str | None


class UserTypingPayload(BaseModel):
    chat_id: str
