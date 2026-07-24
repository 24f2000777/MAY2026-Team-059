from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)


class ChatMessageOut(BaseModel):
    role: str
    message: str
    created_at: datetime | None = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageOut]
