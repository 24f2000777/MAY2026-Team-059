from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ComplaintCategory(str, Enum):
    ROAD = "road"
    POTHOLE = "pothole"
    STREETLIGHT = "streetlight"
    DRAINAGE = "drainage"
    GARBAGE = "garbage"
    WATER_SUPPLY = "water_supply"
    SEWAGE = "sewage"
    TRAFFIC = "traffic"
    ELECTRICITY = "electricity"
    OTHER = "other"


class ComplaintStatus(str, Enum):
    """Complaint states used by the complaint model and API."""

    SUBMITTED = "submitted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ComplaintLocation(BaseModel):
    """
    Complaint location.

    Either:
    - latitude + longitude, OR
    - address

    must be provided.
    """

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="GPS latitude",
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="GPS longitude",
    )

    address: str | None = Field(
        default=None,
        max_length=250,
        description="Address, ward, or landmark",
    )

    @model_validator(mode="after")
    def validate_location(self):
        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None
        has_address = bool(self.address and self.address.strip())

        if has_latitude != has_longitude:
            raise ValueError("Latitude and longitude must be provided together.")

        if not has_address and not (has_latitude and has_longitude):
            raise ValueError("Either latitude and longitude or address must be provided.")

        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latitude": 23.0225,
                "longitude": 72.5714,
                "address": "Near Patel Chowk, Patan",
            }
        }
    )


class ComplaintCreate(BaseModel):
    """
    Request schema for POST /complaints.
    """

    title: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="Complaint title",
    )

    description: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Detailed complaint description",
    )

    category: ComplaintCategory = Field(
        ...,
        description="Complaint category",
    )

    location: ComplaintLocation = Field(
        ...,
        description="Complaint location",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Large pothole on main road",
                "description": "There is a dangerous pothole near the school gate causing accidents.",
                "category": "pothole",
                "location": {
                    "latitude": 23.0225,
                    "longitude": 72.5714,
                    "address": "Near Patel Chowk, Patan",
                },
            }
        }
    )


class ComplaintResponse(BaseModel):
    """
    Response schema for successful complaint creation.
    """

    id: UUID

    status: ComplaintStatus

    priority_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="ML-generated priority score",
    )

    category: ComplaintCategory

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "submitted",
                "priority_score": 85,
                "category": "pothole",
                "created_at": "2026-07-07T21:00:00Z",
            }
        },
    )
