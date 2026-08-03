from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreateRequest(BaseModel):
    """Request schema for POST /complaints/{id}/feedback."""

    score: int = Field(..., ge=1, le=5, description="Rating, 1 to 5 stars")
    feedback: Optional[str] = Field(default=None, max_length=1000, description="Optional written feedback")


class FeedbackOut(BaseModel):
    """One rating, backing GET /complaints/{id}/feedback and the officer/summary views below."""

    id: UUID
    complaint_id: UUID
    citizen_id: UUID
    score: int
    feedback: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OfficerRatingsResponse(BaseModel):
    """Response schema for GET /feedback/officer/{id}."""

    officer_id: UUID
    officer_name: str
    average_score: Optional[float] = Field(None, description="None if the officer has no ratings yet")
    total_ratings: int
    ratings: list[FeedbackOut] = Field(default_factory=list)


class FeedbackSummaryResponse(BaseModel):
    """Response schema for GET /feedback/summary."""

    average_score: Optional[float] = Field(None, description="None if the platform has no ratings yet")
    total_ratings: int
    score_distribution: dict[int, int] = Field(
        default_factory=dict,
        description="Count of ratings at each star value, 1 through 5",
    )
