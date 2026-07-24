"""
Design for POST /complaints/{id}/updates (internal notes)

This module defines the request and response schema for officer/admin-only
internal notes attached to a complaint.

Requirements covered:
- Request body carries note text only; author is taken from the JWT claim
  on the server side and is never accepted from the client.
- Each note is stored as a separate row in the database so multiple notes
  can accumulate over time instead of using one overwritable field.
- Notes are marked as internal-only and should not be included in citizen
  facing response payloads.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from enum import Enum

# In production, import ROLE_STAFF and ROLE_ADMIN from app.utils.constants
class UserRole(str, Enum):
    """User roles in the NAGRIK AI system."""
    STAFF = "staff"
    ADMIN = "admin"


class ComplaintInternalNoteCreateRequest(BaseModel):
    """
    Request body for POST /complaints/{id}/updates.

    The author is derived from the authenticated JWT and must not be supplied
    by the client.
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
                "note_text": "Spoke with resident and scheduled a follow-up inspection for tomorrow."
            }
        }
    )


class ComplaintInternalNoteAuthor(BaseModel):
    """Author summary extracted from the authenticated user context."""

    id: UUID = Field(..., description="Authenticated user ID from JWT")
    name: str = Field(..., description="Display name of the author")
    role: UserRole = Field(..., description="Role of the author (staff/admin)")


class ComplaintInternalNote(BaseModel):
    """
    Internal note stored as a distinct record for the complaint.

    This model is intended for staff/admin-only visibility and should never
    be returned by citizen-facing endpoints.
    """

    id: UUID = Field(..., description="Unique note ID")
    complaint_id: UUID = Field(..., description="Complaint ID the note belongs to")
    note_text: str = Field(..., description="The note content")
    author: ComplaintInternalNoteAuthor = Field(..., description="The user who created the note")
    created_at: datetime = Field(..., description="Server-generated timestamp")
    visibility: str = Field(
        default="internal",
        description="Internal-only visibility marker; never exposed to citizens",
    )

    model_config = ConfigDict(from_attributes=True)


class ComplaintInternalNoteResponse(BaseModel):
    """Single-note response payload for internal users."""

    note: ComplaintInternalNote


class ComplaintInternalNoteListResponse(BaseModel):
    """Collection response for internal users to view all historical notes."""

    notes: list[ComplaintInternalNote] = Field(
        default_factory=list,
        description="Ordered list of notes from oldest to newest",
    )


class ComplaintInternalNotesTableDesign(BaseModel):
    """
    Database design guidance.

    Use one row per note in a dedicated table rather than a single field on the
    complaints table. This allows multiple notes over time and preserves history.
    """

    table_name: str = "complaint_internal_notes"
    columns: dict[str, str] = Field(
        default_factory=lambda: {
            "id": "UUID primary key",
            "complaint_id": "UUID foreign key -> complaints.id",
            "note_text": "TEXT not null",
            "author_id": "UUID foreign key -> users.id",
            "author_name": "VARCHAR(255)",
            "author_role": "VARCHAR(50)",
            "created_at": "TIMESTAMP not null",
        },
        description="Suggested table columns for persistent multi-note storage",
    )

    note: str = Field(
        default="Store one note per row; do not overwrite a single complaints.notes field",
        description="Design rule for maintaining note history",
    )


class ComplaintInternalNoteVisibilityPolicy(BaseModel):
    """Visibility contract for API access control."""

    accessible_to: list[UserRole] = Field(
        default_factory=lambda: [UserRole.STAFF, UserRole.ADMIN],
        description="Roles allowed to read/write internal notes",
    )
    hidden_from: list[str] = Field(
        default_factory=lambda: ["citizen"],
        description="Roles that must never receive these notes in API responses",
    )
    include_in_citizen_endpoints: bool = Field(default=False)
