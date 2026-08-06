from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)

    # Optional GPS coords from the chat UI's "share location" button.
    # Sent on every message once captured (not just the turn it was
    # clicked on), since the conversation may take several more turns
    # before Nagrik Saathi actually has enough to file a complaint,
    # and whichever turn does the filing is the one that needs them.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_coords_paired(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must both be provided together.")
        return self


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
