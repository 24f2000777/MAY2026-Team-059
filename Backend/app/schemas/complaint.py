from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Location error codes, distinct from the generic VAL_001 every other
# request-validation failure gets in app/core/exception_handlers.py.
# Raised as LocationValidationError (a ValueError subclass) so pydantic's
# model_validator still catches and wraps it normally; the handler then
# recovers the specific code from the message instead of collapsing every
# validation failure into VAL_001.
VAL_001 = "VAL_001"
VAL_002 = "VAL_002"

LOCATION_ERROR_MESSAGES = {
    VAL_001: "Either latitude and longitude or address must be provided.",
    VAL_002: "Latitude and longitude must be provided together.",
}


class LocationValidationError(ValueError):
    """
    Raised by ComplaintLocation.validate_location for a specific,
    identifiable location error. Subclasses ValueError (not Exception)
    so pydantic's model_validator(mode="after") catches and wraps it the
    same way it wraps any other ValueError, str(self) is "CODE: message",
    which app/core/exception_handlers.py's handle_validation_error parses
    back out of pydantic's ctx.error field to assign the right error_code
    instead of the generic VAL_001 fallback.
    """

    def __init__(self, error_code: str, message: str, field: str = "location"):
        self.error_code = error_code
        self.message = message
        self.field = field
        super().__init__(f"{error_code}: {message}")


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
            raise LocationValidationError(VAL_002, LOCATION_ERROR_MESSAGES[VAL_002])

        if not has_address and not (has_latitude and has_longitude):
            raise LocationValidationError(VAL_001, LOCATION_ERROR_MESSAGES[VAL_001])

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


# =====================================================
# Complaint Status State Machine
#
# submitted --approve--> approved --start--> in_progress --resolve--> resolved
#     \                       \
#      \--reject--> rejected   \--reject--> rejected
#
# start/resolve additionally require the complaint to already be
# assigned (see PATCH /complaints/{id}/assign in a separate PR) — a
# staff member can only start/resolve their own assigned work, an
# admin can act on any complaint regardless of assignee. See
# complaint_service.py's TRANSITIONS table for the actual rules this
# diagram summarizes.
# =====================================================

class ComplaintTransitionRequest(BaseModel):
    """
    Request body for PATCH /complaints/{id}/approve, /start, and
    /resolve — all three take the same shape, an optional note about
    the transition. /reject uses ComplaintRejectRequest instead,
    since a rejection reason is required, not optional.
    """

    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional note about this transition",
    )

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped or None
        return v

    model_config = ConfigDict(
        json_schema_extra={"example": {"notes": "Confirmed with the ward office, proceeding."}}
    )


class ComplaintRejectRequest(BaseModel):
    """Request body for PATCH /complaints/{id}/reject. A reason is required, not optional."""

    reason: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Why this complaint is being rejected",
    )

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={"example": {"reason": "Duplicate of an already-filed complaint in this ward."}}
    )


class ComplaintStatusResponse(BaseModel):
    """
    Response schema shared by all four transition endpoints
    (approve/reject/start/resolve). Deliberately smaller than
    ComplaintAssignResponse, this only needs to confirm the new state,
    not the whole complaint record.
    """

    id: UUID
    status: str
    assigned_to: Optional[UUID] = None
    reject_reason: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "approved",
                "assigned_to": None,
                "reject_reason": None,
                "updated_at": "2026-07-24T10:15:00Z",
            }
        },
    )
