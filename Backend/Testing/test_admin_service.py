"""
Pytest suite for admin-only resource management
(app/services/admin_service.py): staff account creation (backing POST
/admin/users) and department CRUD (#146, backing /admin/departments).

Hits real Supabase, same reasoning as the other unmocked service
suites in this project.
"""

import uuid

import pytest

from app.core.database import AsyncSessionLocal
from app.model import Complaint, User
from app.schemas.complaint import ComplaintCreate, ComplaintLocation
from app.services.admin_service import (
    create_department,
    create_staff_account,
    delete_department,
    list_departments,
    list_officers,
    update_department_description,
)
from app.services.complaint_service import create_complaint
from app.utils.exceptions import (
    DepartmentInUseError,
    DepartmentNameAlreadyExistsError,
    DepartmentNotFoundError,
    EmailAlreadyExistsError,
    PhoneAlreadyExistsError,
)


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def citizen(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Admin Service Citizen",
        email=f"pytest-admin-service-citizen-{uuid.uuid4()}@example.com",
        role="citizen",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    yield user
    await db.delete(user)
    await db.commit()


def _unique_email() -> str:
    return f"pytest-admin-service-{uuid.uuid4()}@example.com"


def _unique_phone() -> str:
    return f"9{uuid.uuid4().int % 10**9:09d}"


def _unique_department_name() -> str:
    return f"Pytest Department {uuid.uuid4()}"


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


class TestCreateDepartment:
    async def test_creates_a_department(self, db):
        name = _unique_department_name()

        department = await create_department(name, "A department made up for a test.", db)
        await db.commit()

        assert department.id is not None
        assert department.name == name
        assert department.description == "A department made up for a test."

        await db.delete(department)
        await db.commit()

    async def test_rejects_a_duplicate_name(self, db):
        name = _unique_department_name()
        first = await create_department(name, None, db)
        await db.commit()

        with pytest.raises(DepartmentNameAlreadyExistsError):
            await create_department(name, "Different description.", db)

        await db.delete(first)
        await db.commit()


class TestListDepartments:
    async def test_includes_a_newly_created_department(self, db):
        department = await create_department(_unique_department_name(), None, db)
        await db.commit()

        departments = await list_departments(db)

        assert any(d.id == department.id for d in departments)

        await db.delete(department)
        await db.commit()


class TestUpdateDepartmentDescription:
    async def test_updates_the_description(self, db):
        department = await create_department(_unique_department_name(), "Old description.", db)
        await db.commit()

        updated = await update_department_description(department.id, "New description.", db)
        await db.commit()

        assert updated.description == "New description."
        assert updated.name == department.name

        await db.delete(department)
        await db.commit()

    async def test_rejects_a_nonexistent_department(self, db):
        with pytest.raises(DepartmentNotFoundError):
            await update_department_description(uuid.uuid4(), "New description.", db)


class TestDeleteDepartment:
    async def test_deletes_an_unused_department(self, db):
        department = await create_department(_unique_department_name(), None, db)
        await db.commit()

        await delete_department(department.id, db)
        await db.commit()

        departments = await list_departments(db)
        assert all(d.id != department.id for d in departments)

    async def test_rejects_a_nonexistent_department(self, db):
        with pytest.raises(DepartmentNotFoundError):
            await delete_department(uuid.uuid4(), db)

    async def test_rejects_deleting_a_department_with_assigned_staff(self, db):
        department = await create_department(_unique_department_name(), None, db)
        staff = await create_staff_account("Officer With Dept", _unique_phone(), _unique_email(), "TestPass@123", db)
        staff.department_id = department.id
        await db.commit()

        with pytest.raises(DepartmentInUseError):
            await delete_department(department.id, db)

        staff.department_id = None
        await db.commit()
        await db.delete(staff)
        await db.delete(department)
        await db.commit()

    async def test_rejects_deleting_a_department_with_routed_complaints(self, db, citizen):
        department = await create_department(_unique_department_name(), None, db)
        data = ComplaintCreate(
            title="Large pothole on main road",
            description="There is a dangerous pothole near the school gate causing accidents daily.",
            category="pothole",
            location=ComplaintLocation(address="Near Patel Chowk, Patan"),
        )
        complaint = await create_complaint(citizen.id, data, db)
        complaint.department_id = department.id
        await db.commit()

        with pytest.raises(DepartmentInUseError):
            await delete_department(department.id, db)

        await db.delete(complaint)
        await db.delete(department)
        await db.commit()
