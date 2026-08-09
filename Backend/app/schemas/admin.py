from datetime import datetime
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


class StaffAccountOut(BaseModel):
    """Response schema for POST /admin/users."""

    id: UUID
    name: str
    phone: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OfficerListResponse(BaseModel):
    """Response schema for GET /admin/officers."""

    officers: list[StaffAccountOut] = Field(default_factory=list)


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
