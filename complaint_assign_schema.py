"""
Complaint Assignment Schema Design

This module defines the request and response schemas for the
PATCH /complaints/{id}/assign endpoint, which allows admins to assign
complaints to officers.

Security: Only users with 'admin' role can call this endpoint.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from enum import Enum


class UserRole(str, Enum):
    """User roles in the NAGRIK AI system."""
    CITIZEN = "citizen"
    OFFICER = "officer"
    ADMIN = "admin"


class ComplaintAssignRequest(BaseModel):
    """
    Request schema for PATCH /complaints/{id}/assign
    
    This schema is used when an admin assigns a complaint to an officer.
    
    Security Requirements:
    - Only users with role='admin' can call this endpoint
    - The assigned officer must exist and have role='officer'
    - The complaint must exist and be in an assignable state
    
    Validation Rules:
    - assigned_to is required (UUID of the officer)
    - assigned_to must be a valid UUID
    """
    
    assigned_to: UUID = Field(
        ...,
        description="UUID of the officer to assign the complaint to",
    )
    
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional notes about the assignment (e.g., priority, special instructions)",
    )
    
    @field_validator('assigned_to')
    @classmethod
    def validate_assigned_to(cls, v: UUID) -> UUID:
        """
        Validate that assigned_to is a valid UUID.
        
        Additional validation should be performed at the service layer:
        - Check if the user exists in the database
        - Check if the user has role='officer'
        - Check if the officer is active
        """
        if v.version != 4:
            raise ValueError("assigned_to must be a valid UUID v4")
        return v
    
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate notes field if provided."""
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
                    "notes": "High priority - assign senior officer"
                },
                {
                    "assigned_to": "550e8400-e29b-41d4-a716-446655440001"
                }
            ]
        }
    )


class OfficerSummary(BaseModel):
    """
    Summary information about the assigned officer.
    
    This is included in the response to provide context about
    who the complaint has been assigned to.
    """
    
    id: UUID = Field(..., description="Officer's user ID")
    name: str = Field(..., description="Officer's full name")
    role: UserRole = Field(..., description="User role (should be 'officer')")
    department: Optional[str] = Field(
        default=None,
        description="Officer's department (e.g., 'roads', 'sanitation')"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Rajesh Kumar",
                "role": "officer",
                "department": "roads"
            }
        }
    )


class ComplaintAssignResponse(BaseModel):
    """
    Response schema for PATCH /complaints/{id}/assign
    
    Returns the updated complaint with assignment details populated.
    """
    
    id: UUID = Field(..., description="Complaint ID")
    title: str = Field(..., description="Complaint title")
    description: str = Field(..., description="Complaint description")
    category: str = Field(..., description="Complaint category")
    status: str = Field(..., description="Current complaint status")
    priority_score: int = Field(..., description="ML-generated priority score (0-100)")
    
    assigned_to: Optional[UUID] = Field(
        default=None,
        description="UUID of the assigned officer (populated after assignment)"
    )
    
    officer_details: Optional[OfficerSummary] = Field(
        default=None,
        description="Details of the assigned officer (populated after assignment)"
    )
    
    citizen_id: UUID = Field(..., description="UUID of the citizen who created the complaint")
    
    assigned_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the complaint was assigned"
    )
    
    assigned_by: Optional[UUID] = Field(
        default=None,
        description="UUID of the admin who performed the assignment"
    )
    
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
                    "role": "officer",
                    "department": "roads"
                },
                "citizen_id": "999e8877-e66b-21d3-b456-526614174999",
                "assigned_at": "2026-07-24T00:30:00Z",
                "assigned_by": "111e2222-e33b-44d3-c556-626614174111",
                "created_at": "2026-07-23T21:00:00Z",
                "updated_at": "2026-07-24T00:30:00Z"
            }
        }
    )


class AssignmentValidationError(Exception):
    """Custom exception for assignment validation failures."""
    
    def __init__(self, error_code: str, message: str, field: Optional[str] = None):
        self.error_code = error_code
        self.message = message
        self.field = field
        super().__init__(message)


class AssignmentErrorCodes:
    """Error codes for assignment operations."""
    
    # Validation errors
    INVALID_OFFICER_ID = "ASSIGN_001"
    OFFICER_NOT_FOUND = "ASSIGN_002"
    OFFICER_NOT_ACTIVE = "ASSIGN_003"
    OFFICER_NOT_OFFICER_ROLE = "ASSIGN_004"
    
    # Complaint errors
    COMPLAINT_NOT_FOUND = "ASSIGN_005"
    COMPLAINT_ALREADY_ASSIGNED = "ASSIGN_006"
    COMPLAINT_NOT_ASSIGNABLE = "ASSIGN_007"
    
    # Permission errors
    FORBIDDEN_NON_ADMIN = "ASSIGN_008"
    
    @classmethod
    def get_error_details(cls, error_code: str, message: str, field: Optional[str] = None) -> dict:
        """
        Get standardized error response details.
        
        Args:
            error_code: The error code from this class
            message: Human-readable error message
            field: Optional field name that caused the error
            
        Returns:
            dict: Error details in standard API format
        """
        error_dict = {
            "error": {
                "code": error_code,
                "message": message,
                "details": []
            }
        }
        
        if field:
            error_dict["error"]["details"].append({
                "field": field,
                "message": message
            })
        
        return error_dict


# Example usage and validation
if __name__ == "__main__":
    print("Complaint Assignment Schema Examples\n")
    print("=" * 60)
    
    # Example 1: Valid assignment request
    print("\n1. Valid Assignment Request:")
    assign_request = ComplaintAssignRequest(
        assigned_to=UUID("550e8400-e29b-41d4-a716-446655440000"),
        notes="High priority - assign senior officer"
    )
    print(f"   assigned_to: {assign_request.assigned_to}")
    print(f"   notes: {assign_request.notes}")
    
    # Example 2: Valid assignment request without notes
    print("\n2. Valid Assignment Request (without notes):")
    assign_request2 = ComplaintAssignRequest(
        assigned_to=UUID("550e8400-e29b-41d4-a716-446655440001")
    )
    print(f"   assigned_to: {assign_request2.assigned_to}")
    print(f"   notes: {assign_request2.notes}")
    
    # Example 3: Valid assignment response
    print("\n3. Valid Assignment Response:")
    response = ComplaintAssignResponse(
        id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        title="Large pothole on main road",
        description="There is a dangerous pothole near the school gate.",
        category="pothole",
        status="in_progress",
        priority_score=85,
        assigned_to=UUID("550e8400-e29b-41d4-a716-446655440000"),
        officer_details=OfficerSummary(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            name="Rajesh Kumar",
            role=UserRole.OFFICER,
            department="roads"
        ),
        citizen_id=UUID("999e8877-e66b-21d3-b456-526614174999"),
        assigned_at=datetime.now(),
        assigned_by=UUID("111e2222-e33b-44d3-c556-626614174111"),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    print(f"   Complaint ID: {response.id}")
    print(f"   Assigned to: {response.officer_details.name if response.officer_details else 'N/A'}")
    print(f"   Status: {response.status}")
    
    # Example 4: Error response examples
    print("\n4. Error Response Examples:")
    
    error1 = AssignmentErrorCodes.get_error_details(
        AssignmentErrorCodes.OFFICER_NOT_FOUND,
        "Officer with specified ID not found",
        "assigned_to"
    )
    print(f"   Officer Not Found: {error1}")
    
    error2 = AssignmentErrorCodes.get_error_details(
        AssignmentErrorCodes.FORBIDDEN_NON_ADMIN,
        "Only admin users can assign complaints"
    )
    print(f"   Forbidden (Non-Admin): {error2}")
    
    error3 = AssignmentErrorCodes.get_error_details(
        AssignmentErrorCodes.COMPLAINT_ALREADY_ASSIGNED,
        "Complaint is already assigned to an officer",
        "assigned_to"
    )
    print(f"   Already Assigned: {error3}")
    
    print("\n" + "=" * 60)
    print("Schema validation complete.")
