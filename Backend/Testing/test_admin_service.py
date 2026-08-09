"""
Pytest suite for admin-only resource management
(app/services/admin_service.py): staff account creation (backing POST
/admin/users) and department CRUD (#146, backing /admin/departments).

Hits real Supabase, same reasoning as the other unmocked service
suites in this project.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.model import Complaint, User
from app.schemas.complaint import ComplaintCreate, ComplaintLocation
from app.services.admin_service import (
    create_department,
    create_staff_account,
    delete_department,
    get_user_detail,
    list_departments,
    list_officers,
    list_users,
    update_department_description,
    update_user_role,
    update_user_status,
)
from app.services.complaint_service import create_complaint
from app.utils.exceptions import (
    CannotChangeAdminRoleError,
    CannotDeactivateLastAdminError,
    CannotModifySelfError,
    DepartmentInUseError,
    DepartmentNameAlreadyExistsError,
    DepartmentNotFoundError,
    EmailAlreadyExistsError,
    PhoneAlreadyExistsError,
    UserNotFoundError,
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


class TestListUsers:
    async def test_filters_by_role(self, db, citizen):
        staff = await create_staff_account("Officer Filter", _unique_phone(), _unique_email(), "TestPass@123", db)
        await db.commit()

        users, total = await list_users(role="staff", is_active=None, search=None, page=1, per_page=100, db=db)

        assert any(u.id == staff.id for u in users)
        assert all(u.role == "staff" for u in users)
        assert total >= 1

        await db.delete(staff)
        await db.commit()

    async def test_search_matches_name(self, db):
        staff = await create_staff_account(
            "Zzyzx Unique Searchable Name", _unique_phone(), _unique_email(), "TestPass@123", db
        )
        await db.commit()

        users, total = await list_users(
            role=None, is_active=None, search="Zzyzx Unique Searchable", page=1, per_page=20, db=db
        )

        assert total == 1
        assert users[0].id == staff.id

        await db.delete(staff)
        await db.commit()

    async def test_filters_by_is_active(self, db):
        staff = await create_staff_account("Officer Active", _unique_phone(), _unique_email(), "TestPass@123", db)
        await db.commit()

        active_users, _ = await list_users(role=None, is_active=True, search=None, page=1, per_page=100, db=db)
        assert any(u.id == staff.id for u in active_users)

        inactive_users, _ = await list_users(role=None, is_active=False, search=None, page=1, per_page=100, db=db)
        assert all(u.id != staff.id for u in inactive_users)

        await db.delete(staff)
        await db.commit()


class TestGetUserDetail:
    async def test_returns_a_citizens_filed_complaints(self, db, citizen):
        data = ComplaintCreate(
            title="Broken streetlight near market",
            description="The streetlight outside the main market has been broken for a week.",
            category="streetlight",
            location=ComplaintLocation(address="Market Road, Patan"),
        )
        complaint = await create_complaint(citizen.id, data, db)
        await db.commit()

        user, complaints = await get_user_detail(citizen.id, db)

        assert user.id == citizen.id
        assert any(c.id == complaint.id for c in complaints)

        await db.delete(complaint)
        await db.commit()

    async def test_rejects_a_nonexistent_user(self, db):
        with pytest.raises(UserNotFoundError):
            await get_user_detail(uuid.uuid4(), db)


class TestUpdateUserStatus:
    async def test_deactivates_another_user(self, db, citizen):
        admin = User(
            phone=_unique_phone(),
            name="Pytest Admin Actor",
            email=_unique_email(),
            role="admin",
            hashed_password="x",
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        updated = await update_user_status(citizen.id, False, admin, db)
        await db.commit()

        assert updated.is_active is False

        await db.delete(admin)
        await db.commit()

    async def test_rejects_self_deactivation(self, db, citizen):
        with pytest.raises(CannotModifySelfError):
            await update_user_status(citizen.id, False, citizen, db)

    async def test_rejects_deactivating_the_last_active_admin(self, db, citizen):
        # This is a shared DB with a real platform admin already in it,
        # so "last admin" has to be engineered: temporarily deactivate
        # every other currently-active admin, restoring them in a
        # finally block no matter what happens in the test body.
        result = await db.execute(select(User).where(User.role == "admin", User.is_active == True))  # noqa: E712
        other_active_admins = result.scalars().all()

        admin = User(
            phone=_unique_phone(),
            name="Pytest Sole Admin",
            email=_unique_email(),
            role="admin",
            hashed_password="x",
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        for other in other_active_admins:
            other.is_active = False
        await db.commit()

        try:
            with pytest.raises(CannotDeactivateLastAdminError):
                await update_user_status(admin.id, False, citizen, db)
        finally:
            for other in other_active_admins:
                other.is_active = True
            await db.commit()
            await db.delete(admin)
            await db.commit()

    async def test_rejects_a_nonexistent_user(self, db, citizen):
        with pytest.raises(UserNotFoundError):
            await update_user_status(uuid.uuid4(), False, citizen, db)


class TestUpdateUserRole:
    async def test_changes_a_citizens_role_to_staff(self, db, citizen):
        admin = User(
            phone=_unique_phone(),
            name="Pytest Admin Role Actor",
            email=_unique_email(),
            role="admin",
            hashed_password="x",
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        updated = await update_user_role(citizen.id, "staff", admin, db)
        await db.commit()

        assert updated.role == "staff"

        await db.delete(admin)
        await db.commit()

    async def test_rejects_self_role_change(self, db, citizen):
        with pytest.raises(CannotModifySelfError):
            await update_user_role(citizen.id, "staff", citizen, db)

    async def test_rejects_changing_the_admin_accounts_role(self, db, citizen):
        admin = User(
            phone=_unique_phone(),
            name="Pytest Untouchable Admin",
            email=_unique_email(),
            role="admin",
            hashed_password="x",
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        with pytest.raises(CannotChangeAdminRoleError):
            await update_user_role(admin.id, "staff", citizen, db)

        await db.delete(admin)
        await db.commit()

    async def test_rejects_a_nonexistent_user(self, db, citizen):
        with pytest.raises(UserNotFoundError):
            await update_user_role(uuid.uuid4(), "staff", citizen, db)
