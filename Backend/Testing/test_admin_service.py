"""
Pytest suite for admin-only staff account creation
(app/services/admin_service.py, backing POST /admin/users).

Hits real Supabase, same reasoning as the other unmocked service
suites in this project.
"""

import uuid

import pytest

from app.core.database import AsyncSessionLocal
from app.model import User
from app.services.admin_service import create_staff_account, list_officers
from app.utils.exceptions import EmailAlreadyExistsError, PhoneAlreadyExistsError


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


def _unique_email() -> str:
    return f"pytest-admin-service-{uuid.uuid4()}@example.com"


def _unique_phone() -> str:
    return f"9{uuid.uuid4().int % 10**9:09d}"


class TestCreateStaffAccount:
    async def test_creates_an_active_staff_account(self, db):
        email = _unique_email()
        phone = _unique_phone()

        staff = await create_staff_account("Officer One", phone, email, "TestPass@123", db)
        await db.commit()

        assert staff.id is not None
        assert staff.role == "staff"
        assert staff.is_active is True
        assert staff.email == email
        assert staff.phone == phone
        assert staff.hashed_password != "TestPass@123"

        await db.delete(staff)
        await db.commit()

    async def test_rejects_a_duplicate_email(self, db):
        email = _unique_email()
        first = await create_staff_account("Officer One", _unique_phone(), email, "TestPass@123", db)
        await db.commit()

        with pytest.raises(EmailAlreadyExistsError):
            await create_staff_account("Officer Two", _unique_phone(), email, "TestPass@456", db)

        await db.delete(first)
        await db.commit()

    async def test_rejects_a_duplicate_phone(self, db):
        phone = _unique_phone()
        first = await create_staff_account("Officer One", phone, _unique_email(), "TestPass@123", db)
        await db.commit()

        with pytest.raises(PhoneAlreadyExistsError):
            await create_staff_account("Officer Two", phone, _unique_email(), "TestPass@456", db)

        await db.delete(first)
        await db.commit()


class TestListOfficers:
    async def test_includes_a_newly_created_officer(self, db):
        staff = await create_staff_account("Officer Findable", _unique_phone(), _unique_email(), "TestPass@123", db)
        await db.commit()

        officers = await list_officers(db)

        assert any(o.id == staff.id for o in officers)
        assert all(o.role == "staff" for o in officers)

        await db.delete(staff)
        await db.commit()
