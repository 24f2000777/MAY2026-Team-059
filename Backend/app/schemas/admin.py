from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateStaffRequest(BaseModel):
    """
    Request body for POST /admin/users. Admin-only, and deliberately
    has no role field, this always creates a staff account, never
    another admin, the platform has exactly one admin and it's never
    created through this endpoint (see scripts/create_admin.py).
    """

    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    department_id: UUID | None = Field(
        default=None,
        description="Optional, assigns the new staff account to this department immediately.",
    )


class StaffAccountOut(BaseModel):
    """Response schema for POST /admin/users."""

    id: UUID
    name: str
    phone: str
    email: str
    role: str
    is_active: bool
    department_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OfficerListResponse(BaseModel):
    """Response schema for GET /admin/officers."""

    officers: list[StaffAccountOut] = Field(default_factory=list)


# Same shape as StaffAccountOut (id/name/phone/email/role/is_active/
# created_at), aliased rather than duplicated: the general user list
# below can return any role, not just staff, "UserOut" reads right in
# that context where "StaffAccountOut" wouldn't for a citizen row.
UserOut = StaffAccountOut


class UserListResponse(BaseModel):
    """Response schema for GET /admin/users."""

    users: list[UserOut] = Field(default_factory=list)


class UserComplaintSummary(BaseModel):
    """One row in GET /admin/users/{id}'s complaint history."""

    id: UUID
    title: str
    category: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(BaseModel):
    """
    Response schema for GET /admin/users/{id}. complaints covers
    both directions a user can relate to a complaint: ones a citizen
    filed, or ones assigned to a staff member, whichever applies to
    this particular user's role.
    """

    user: UserOut
    complaints: list[UserComplaintSummary] = Field(default_factory=list)


class UpdateUserStatusRequest(BaseModel):
    """Request body for PATCH /admin/users/{id}/status."""

    is_active: bool


class UpdateUserRoleRequest(BaseModel):
    """
    Request body for PATCH /admin/users/{id}/role. Deliberately only
    accepts citizen/staff, promoting to admin isn't possible through
    this endpoint at all, the platform has exactly one admin by
    design (see scripts/create_admin.py).
    """

    role: Literal["citizen", "staff"]


class AssignStaffDepartmentRequest(BaseModel):
    """
    Request body for PATCH /admin/users/{id}/department. department_id
    is nullable on purpose, sending null unassigns the staff member
    from whatever department they're currently in.
    """

    department_id: UUID | None = None


class DepartmentCreateRequest(BaseModel):
    """
    Request body for POST /admin/departments. See
    admin_service.create_department for what a name outside the fixed
    DEPARTMENT_NAMES list does and doesn't get you.
    """

    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class DepartmentUpdateRequest(BaseModel):
    """
    Request body for PATCH /admin/departments/{id}. name isn't here on
    purpose, it isn't editable through this endpoint, see
    admin_service.update_department_description for why.
    """

    description: str = Field(..., max_length=1000)


class DepartmentOut(BaseModel):
    """Response schema for department CRUD endpoints."""

    id: UUID
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepartmentListResponse(BaseModel):
    """Response schema for GET /admin/departments."""

    departments: list[DepartmentOut] = Field(default_factory=list)
