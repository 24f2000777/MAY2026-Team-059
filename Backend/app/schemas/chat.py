from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)


class ChatFiledComplaint(BaseModel):
    """
    Lightweight summary of a complaint the conversation just filed,
    attached to a /chat/message reply so the frontend can show a
    confirmation without a second round trip to GET /complaints/{id}.
    Deliberately smaller than ComplaintResponse's sibling schemas,
    just enough to confirm what got filed and how it was scored.
    """

    id: UUID
    title: str
    category: str
    priority_score: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    session_id: str
    reply: str
    complaint: ChatFiledComplaint | None = Field(
        default=None,
        description="Set only on the turn that actually filed a complaint, null otherwise.",
    )


class ChatMessageOut(BaseModel):
    role: str
    message: str
    created_at: datetime | None = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageOut]
