"""
Complaint Assignment Schema Design

This module defines the request and response schemas for the
PATCH /complaints/{id}/assign endpoint, which allows admins to assign
complaints to staff members.

Security: Only users with 'admin' role can call this endpoint.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from enum import Enum

# In production, import ROLE_CITIZEN, ROLE_STAFF, ROLE_ADMIN from app.utils.constants
class UserRole(str, Enum):
    """User roles in the NAGRIK AI system."""
    CITIZEN = "citizen"
    STAFF = "staff"
    ADMIN = "admin"


class ComplaintAssignRequest(BaseModel):
    """
    Request schema for PATCH /complaints/{id}/assign
    
    Used when an admin assigns a complaint to a staff member.
    
    Security Requirements:
    - Only users with role='admin' can call this endpoint
    - The assigned staff must exist and have role='staff'
    - The complaint must exist and be in an assignable state
    
    Validation Rules:
    - assigned_to is required (UUID of the staff member)
    - assigned_to must be a valid UUID
    """
    
    assigned_to: UUID = Field(
        ...,
        description="UUID of the staff member to assign the complaint to",
    )
    
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional notes about the assignment (e.g., priority, special instructions)",
    )
    
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Normalize notes field if provided."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "assigned_to": "550e8400-e29b-41d4-a716-446655440000",
                    "notes": "High priority - assign senior staff"
                },
                {
                    "assigned_to": "550e8400-e29b-41d4-a716-446655440001"
                }
            ]
        }
    )


class OfficerSummary(BaseModel):
    """
    Summary information about the assigned staff member.
    
    Note: User model has department_id (UUID FK). Populating department
    requires a join to Department.name, not a direct attribute.
    """
    
    id: UUID = Field(..., description="Staff user ID")
    name: str = Field(..., description="Staff member's full name")
    role: UserRole = Field(..., description="User role (should be 'staff')")
    department: Optional[str] = Field(
        default=None,
        description="Staff member's department name (requires join)"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Rajesh Kumar",
                "role": "staff",
                "department": "roads"
            }
        }
    )


class ComplaintAssignResponse(BaseModel):
    """
    Response schema for PATCH /complaints/{id}/assign
    
    Returns the updated complaint with assignment details populated.
    Assignment events should be logged in ComplaintUpdate, not as new
    columns in Complaint.
    """
    
    id: UUID = Field(..., description="Complaint ID")
    title: str = Field(..., description="Complaint title")
    description: str = Field(..., description="Complaint description")
    category: str = Field(..., description="Complaint category")
    status: str = Field(..., description="Current complaint status")
    priority_score: int = Field(..., description="ML-generated priority score (0-100)")
    
    assigned_to: Optional[UUID] = Field(
        default=None,
        description="UUID of the assigned staff member"
    )
    
    officer_details: Optional[OfficerSummary] = Field(
        default=None,
        description="Details of the assigned staff member"
    )
    
    citizen_id: UUID = Field(..., description="UUID of the citizen who created the complaint")
    
    created_at: datetime = Field(..., description="Complaint creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Large pothole on main road",
                "description": "There is a dangerous pothole near the school gate causing accidents.",
                "category": "pothole",
                "status": "in_progress",
                "priority_score": 85,
                "assigned_to": "550e8400-e29b-41d4-a716-446655440000",
                "officer_details": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Rajesh Kumar",
                    "role": "staff",
                    "department": "roads"
                },
                "citizen_id": "999e8877-e66b-21d3-b456-526614174999",
                "created_at": "2026-07-23T21:00:00Z",
                "updated_at": "2026-07-24T00:30:00Z"
            }
        }
    )
