from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationOut(BaseModel):
    """One notification, backing GET /notifications."""

    id: UUID
    complaint_id: Optional[UUID] = None
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Response schema for GET /notifications."""

    notifications: list[NotificationOut] = Field(default_factory=list)


class UnreadCountResponse(BaseModel):
    """Response schema for GET /notifications/unread-count."""

    unread_count: int


class MarkAllReadResponse(BaseModel):
    """Response schema for PATCH /notifications/read-all."""

    marked_read: int


class NotificationPreferencesRequest(BaseModel):
    """Request schema for POST /notifications/preferences."""

    email_enabled: bool = Field(..., description="Whether to also email the user on new notifications")


class NotificationPreferencesResponse(BaseModel):
    """Response schema for POST /notifications/preferences."""

    email_enabled: bool
