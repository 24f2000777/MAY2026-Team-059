from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.utils.constants import DEPARTMENT_NAMES

# The exact same fixed set app/utils/constants.py uses for AI routing,
# reused here so a staff account can only ever be filed under one of
# these categories, not some arbitrary string an admin typed in.
DepartmentCategory = Literal[*DEPARTMENT_NAMES]


class CreateStaffRequest(BaseModel):
    """
    Request body for POST /admin/users. Admin-only, and deliberately
    has no role field, this always creates a staff account, never
    another admin, the platform has exactly one admin and it's never
    created through this endpoint (see scripts/create_admin.py).

    No email or password here on purpose, see
    admin_service.create_staff_account for how both get generated.
    """

    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    department: DepartmentCategory


class StaffAccountOut(BaseModel):
    """Response schema shared by every admin user-management endpoint."""

    id: UUID
    name: str
    phone: str
    email: str
    role: str
    is_active: bool
    department: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StaffAccountCreatedOut(StaffAccountOut):
    """
    Response schema for POST /admin/users only. generated_password is
    the only place this ever appears in plaintext, only its hash is
    stored, so this is the admin's one chance to see and hand it to
    the new officer.
    """

    generated_password: str


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
    Request body for PATCH /admin/users/{id}/department. department is
    nullable on purpose, sending null unassigns the staff member from
    whatever department they're currently in.
    """

    department: DepartmentCategory | None = None


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
