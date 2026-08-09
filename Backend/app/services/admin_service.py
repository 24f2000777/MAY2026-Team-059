"""
Admin-only resource management: staff account creation (POST
/admin/users) and department CRUD (#146). The platform's one admin
account is never created here, or through any API route, see
scripts/create_admin.py for that.
"""

from sqlalchemy import select

from app.core.security import hash_password
from app.model import Complaint, Department, User
from app.utils.constants import ROLE_STAFF
from app.utils.exceptions import (
    DepartmentInUseError,
    DepartmentNameAlreadyExistsError,
    DepartmentNotFoundError,
    EmailAlreadyExistsError,
    PhoneAlreadyExistsError,
)


async def list_officers(db) -> list[User]:
    """
    Every staff account, newest first, backing GET /admin/officers.
    Used to populate an assignment dropdown, so name is what matters
    most here, not any particular ordering by workload.
    """
    result = await db.execute(
        select(User).where(User.role == ROLE_STAFF).order_by(User.created_at.desc())
    )
    return result.scalars().all()


async def create_staff_account(name: str, phone: str, email: str, password: str, db) -> User:
    """
    Creates a staff account, already active, no OTP/verification
    step, an admin creating an account for a real officer is already
    a trusted action, unlike public self-registration.

    Raises:
        EmailAlreadyExistsError: 409, if the email is already registered.
        PhoneAlreadyExistsError: 409, if the phone is already registered.

    Does not commit, same convention as every other service in this app.
    """
    existing_email = await db.execute(select(User.id).where(User.email == email))
    if existing_email.first() is not None:
        raise EmailAlreadyExistsError("Email is already registered.")

    existing_phone = await db.execute(select(User.id).where(User.phone == phone))
    if existing_phone.first() is not None:
        raise PhoneAlreadyExistsError("Phone number is already registered.")

    staff = User(
        name=name,
        phone=phone,
        email=email,
        role=ROLE_STAFF,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db.add(staff)
    await db.flush()
    return staff


async def list_departments(db) -> list[Department]:
    """Every department, alphabetical, backing GET /admin/departments."""
    result = await db.execute(select(Department).order_by(Department.name))
    return result.scalars().all()


async def create_department(name: str, description: str | None, db) -> Department:
    """
    Creates a new department row.

    Worth knowing: the AI routing pipeline (app/services/routing_service.py)
    asks the LLM to pick from a fixed name list (app/utils/constants.
    DEPARTMENT_NAMES), baked into the LLM's response schema at the
    code level, not read from this table. A department created here
    with a name outside that fixed list is real and usable for manual
    assignment, it just won't ever receive a complaint through
    automatic routing unless DEPARTMENT_NAMES is also updated in code.

    Raises:
        DepartmentNameAlreadyExistsError: 409, if the name is taken.
    """
    existing = await db.execute(select(Department.id).where(Department.name == name))
    if existing.first() is not None:
        raise DepartmentNameAlreadyExistsError("A department with this name already exists.")

    department = Department(name=name, description=description)
    db.add(department)
    await db.flush()
    return department


async def update_department_description(department_id, description: str, db) -> Department:
    """
    Updates a department's description. name is deliberately not
    editable through this: routing_service.route_complaint looks up a
    department by exact name match against whatever the LLM returns,
    renaming one of the fixed DEPARTMENT_NAMES here would silently
    stop that department from ever being auto-routed to again, with
    no error anywhere to explain why.

    Raises:
        DepartmentNotFoundError: 404, if the department doesn't exist.
    """
    department = await db.get(Department, department_id)
    if department is None:
        raise DepartmentNotFoundError("Department not found.")

    department.description = description
    await db.flush()
    return department


async def delete_department(department_id, db) -> None:
    """
    Deletes a department, only if nothing actually references it.
    Both User.department_id and Complaint.department_id are nullable
    FKs with no ON DELETE behavior configured, so an unguarded delete
    would fail with a raw DB IntegrityError, this checks first and
    raises a clear error instead.

    Raises:
        DepartmentNotFoundError: 404, if the department doesn't exist.
        DepartmentInUseError: 409, if any staff or complaint still
            references this department.
    """
    department = await db.get(Department, department_id)
    if department is None:
        raise DepartmentNotFoundError("Department not found.")

    staff_using_it = await db.execute(select(User.id).where(User.department_id == department_id))
    if staff_using_it.first() is not None:
        raise DepartmentInUseError("Cannot delete a department that still has staff assigned to it.")

    complaints_using_it = await db.execute(select(Complaint.id).where(Complaint.department_id == department_id))
    if complaints_using_it.first() is not None:
        raise DepartmentInUseError("Cannot delete a department that still has complaints routed to it.")

    await db.delete(department)
    await db.flush()
