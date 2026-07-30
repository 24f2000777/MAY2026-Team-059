from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

INTERNAL_NOTE_VISIBILITY = "internal"

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
# Complaint Assignment
#
# Built from complaint_assign_schema.py (the reviewed design doc at
# the repo root) — same shape, adapted to reuse this app's real
# ComplaintStatus enum and plain-string User.role instead of the
# design doc's own standalone copies of those.
# =====================================================

class ComplaintAssignRequest(BaseModel):
    """
    Request schema for PATCH /complaints/{id}/assign.

    Only an admin can call this route (enforced by require_roles at
    the route level, not by this schema). assigned_to must be an
    existing user with role='staff' — checked in the service layer,
    since that needs a database lookup this schema can't do on its
    own.
    """

    assigned_to: UUID = Field(
        ...,
        description="UUID of the staff member to assign the complaint to",
    )

    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional notes about the assignment, e.g. priority or special instructions",
    )

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped or None
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "assigned_to": "550e8400-e29b-41d4-a716-446655440000",
                    "notes": "High priority, assign senior staff",
                },
                {"assigned_to": "550e8400-e29b-41d4-a716-446655440001"},
            ]
        }
    )


class StaffSummary(BaseModel):
    """
    Summary of the staff member a complaint was assigned to.
    department requires a join to Department.name (User only has
    department_id), so this is built by hand in the route rather than
    via model_validate(staff_user) directly.
    """

    id: UUID = Field(..., description="Staff user ID")
    name: str = Field(..., description="Staff member's full name")
    role: str = Field(..., description="User role, should be 'staff'")
    department: Optional[str] = Field(
        default=None,
        description="Staff member's department name",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Rajesh Kumar",
                "role": "staff",
                "department": "Roads Department",
            }
        }
    )


class ComplaintAssignResponse(BaseModel):
    """
    Response schema for PATCH /complaints/{id}/assign. Assignment
    events are logged in ComplaintUpdate (see complaint_service.py),
    not as extra columns on Complaint itself. Assigning does not
    change status, it's a separate concern from the actual
    approve/start/resolve/reject state machine.
    """

    id: UUID
    title: str
    description: str
    category: str
    status: str
    priority_score: int

    assigned_to: Optional[UUID] = None
    staff_details: Optional[StaffSummary] = None

    citizen_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Large pothole on main road",
                "description": "There is a dangerous pothole near the school gate causing accidents.",
                "category": "pothole",
                "status": "approved",
                "priority_score": 85,
                "assigned_to": "550e8400-e29b-41d4-a716-446655440000",
                "staff_details": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Rajesh Kumar",
                    "role": "staff",
                    "department": "Roads Department",
                },
                "citizen_id": "999e8877-e66b-21d3-b456-526614174999",
                "created_at": "2026-07-23T21:00:00Z",
                "updated_at": "2026-07-24T00:30:00Z",
            }
        },
    )


# =====================================================
# Complaint Internal Notes
#
# Built from complaint_internal_notes_schema.py (the reviewed design
# doc at the repo root), with one real change: that doc proposes a
# brand new complaint_internal_notes table, but ComplaintUpdate
# already is exactly what it's describing, a table with one row per
# note/event on a complaint rather than one overwritable field. Notes
# added here are ComplaintUpdate rows with old_status/new_status left
# null (a pure note, no status change attached), read back through
# ComplaintUpdate.notes. author name/role stay join-derived rather
# than stored redundantly, which is what this doc's own response
# schema already wanted (its "suggested columns" note contradicted
# its own response model on this point).
# =====================================================

class ComplaintNoteCreateRequest(BaseModel):
    """
    Request schema for POST /complaints/{id}/updates. The author is
    derived from the authenticated JWT (require_roles) and is never
    accepted from the client.
    """

    note_text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Internal note content added by a staff member or admin",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "note_text": "Spoke with resident and scheduled a follow-up inspection for tomorrow.",
            }
        }
    )


class ComplaintNoteAuthor(BaseModel):
    """Author summary, built from a join to User at read time."""

    id: UUID = Field(..., description="Author's user ID")
    name: str = Field(..., description="Author's display name")
    role: str = Field(..., description="Author's role, staff or admin")


class ComplaintNote(BaseModel):
    """
    A single internal note. Staff/admin only, must never be returned
    by a citizen-facing endpoint.
    """

    id: UUID = Field(..., description="Note ID")
    complaint_id: UUID = Field(..., description="Complaint this note belongs to")
    note_text: str = Field(..., description="The note content")
    author: ComplaintNoteAuthor = Field(..., description="The staff/admin user who wrote the note")
    created_at: datetime = Field(..., description="Server-generated timestamp")
    visibility: str = Field(
        default=INTERNAL_NOTE_VISIBILITY,
        description="Internal-only visibility marker, never exposed to citizens",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "7c1e2f3a-9b4d-4e5f-8a6b-1c2d3e4f5a6b",
                "complaint_id": "123e4567-e89b-12d3-a456-426614174000",
                "note_text": "Spoke with resident and scheduled a follow-up inspection for tomorrow.",
                "author": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Rajesh Kumar",
                    "role": "staff",
                },
                "created_at": "2026-07-24T10:15:00Z",
                "visibility": "internal",
            }
        }
    )


class ComplaintNoteListResponse(BaseModel):
    """Response schema for GET /complaints/{id}/updates."""

    notes: list[ComplaintNote] = Field(
        default_factory=list,
        description="Notes ordered oldest to newest",
    )
