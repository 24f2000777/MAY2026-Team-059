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
