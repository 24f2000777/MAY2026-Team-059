"""
Admin-only resource management: staff account creation (POST
/admin/users) and department CRUD (#146). The platform's one admin
account is never created here, or through any API route, see
scripts/create_admin.py for that.
"""

import re
import secrets
import string

from sqlalchemy import func as sa_func
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.model import Complaint, Department, User
from app.utils.constants import ROLE_ADMIN, ROLE_STAFF
from app.utils.exceptions import (
    CannotChangeAdminRoleError,
    CannotDeactivateLastAdminError,
    CannotModifySelfError,
    DepartmentInUseError,
    DepartmentNameAlreadyExistsError,
    DepartmentNotFoundError,
    PhoneAlreadyExistsError,
    UserNotFoundError,
    UserNotStaffError,
)

_STAFF_EMAIL_DOMAIN = "nagrikai.team"


def _slugify_first_name(name: str) -> str:
    first_word = name.strip().split()[0] if name.strip() else ""
    slug = re.sub(r"[^a-z0-9]", "", first_word.lower())
    return slug or "staff"


async def _generate_staff_email(name: str, db) -> str:
    """
    firstname.staff@nagrikai.team, the shared login-email convention
    for every staff account, an admin never picks this. Appends a
    number on collision (two officers can easily share a first name),
    starting at 2 so the first officer with that name keeps the plain
    firstname.staff@ address.
    """
    base = _slugify_first_name(name)
    candidate = f"{base}.staff@{_STAFF_EMAIL_DOMAIN}"
    suffix = 2
    while (await db.execute(select(User.id).where(User.email == candidate))).first() is not None:
        candidate = f"{base}{suffix}.staff@{_STAFF_EMAIL_DOMAIN}"
        suffix += 1
    return candidate


def _generate_staff_password(length: int = 12) -> str:
    """
    A one-time random password for a newly created staff account.
    Only its hash is ever stored, the plaintext is returned to the
    caller exactly once so the admin can hand it to the new officer;
    see StaffAccountCreatedOut. The officer can change it afterwards
    through the existing POST /auth/change-password.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def list_officers(db) -> list[User]:
    """
    Every staff account, newest first, backing GET /admin/officers.
    Used to populate an assignment dropdown, so name is what matters
    most here, not any particular ordering by workload. department is
    eager-loaded so the route can read .department.name without a
    lazy-load (not safe under an async session outside this call).
    """
    result = await db.execute(
        select(User)
        .where(User.role == ROLE_STAFF)
        .options(selectinload(User.department))
        .order_by(User.created_at.desc())
    )
    return result.scalars().all()


async def create_staff_account(name: str, phone: str, department: str, db) -> tuple[User, str]:
    """
    Creates a staff account, already active, no OTP/verification
    step, an admin creating an account for a real officer is already
    a trusted action, unlike public self-registration.

    Unlike a citizen's own registration, the admin doesn't choose an
    email or password here, both are generated: email follows
    firstname.staff@nagrikai.team (_generate_staff_email), password is
    a random one-time secret (_generate_staff_password) returned
    alongside the account so the admin can hand it to the new officer,
    who can change it later via POST /auth/change-password.

    department must be one of the fixed categories (enforced already
    at the schema layer by CreateStaffRequest's DepartmentCategory),
    resolved here to the matching seeded Department row.

    Raises:
        PhoneAlreadyExistsError: 409, if the phone is already registered.
        DepartmentNotFoundError: 404, if department somehow doesn't
            match a real department, shouldn't happen in practice
            since these are seeded at startup (seed_departments).

    Returns (staff, plaintext_password). Does not commit.
    """
    existing_phone = await db.execute(select(User.id).where(User.phone == phone))
    if existing_phone.first() is not None:
        raise PhoneAlreadyExistsError("Phone number is already registered.")

    department_result = await db.execute(select(Department).where(Department.name == department))
    department_row = department_result.scalar_one_or_none()
    if department_row is None:
        raise DepartmentNotFoundError("Department not found.")

    email = await _generate_staff_email(name, db)
    password = _generate_staff_password()

    staff = User(
        name=name,
        phone=phone,
        email=email,
        role=ROLE_STAFF,
        hashed_password=hash_password(password),
        is_active=True,
    )
    staff.department = department_row
    db.add(staff)
    await db.flush()
    return staff, password


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


async def list_users(
    role: str | None,
    is_active: bool | None,
    search: str | None,
    page: int,
    per_page: int,
    db,
) -> tuple[list[User], int]:
    """
    Every user (any role), newest first, backing GET /admin/users.
    search matches name/email/phone by substring, case-insensitive.
    department is eager-loaded, same reasoning as list_officers.
    """
    query = select(User).options(selectinload(User.department))
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
                User.phone.ilike(pattern),
            )
        )

    count_result = await db.execute(select(sa_func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all(), total


async def get_user_detail(user_id, db) -> tuple[User, list[Complaint]]:
    """
    A single user plus their complaint history, backing
    GET /admin/users/{id}. complaints covers both directions a user
    can relate to a complaint: ones a citizen filed, or ones assigned
    to a staff member, whichever applies to this user's role.

    Raises:
        UserNotFoundError: 404, if the user doesn't exist.
    """
    user = await db.get(User, user_id, options=[selectinload(User.department)])
    if user is None:
        raise UserNotFoundError("User not found.")

    result = await db.execute(
        select(Complaint)
        .where(or_(Complaint.citizen_id == user_id, Complaint.assigned_to == user_id))
        .order_by(Complaint.created_at.desc())
    )
    return user, result.scalars().all()


async def update_user_status(user_id, is_active: bool, current_user: User, db) -> User:
    """
    Activates or deactivates a user, backing PATCH /admin/users/{id}/status.

    Raises:
        UserNotFoundError: 404, if the user doesn't exist.
        CannotModifySelfError: 409, deactivating your own account is a
            self-lockout, there's no way back in without a direct DB edit.
        CannotDeactivateLastAdminError: 409, if this would leave the
            platform with zero active admins.
    """
    user = await db.get(User, user_id, options=[selectinload(User.department)])
    if user is None:
        raise UserNotFoundError("User not found.")

    if user.id == current_user.id and not is_active:
        raise CannotModifySelfError("You cannot deactivate your own account.")

    if not is_active and user.role == ROLE_ADMIN:
        # FOR UPDATE locks every currently-active admin row (not just
        # the others), so two concurrent deactivate-a-different-admin
        # requests can't both read "one other admin left" and both
        # succeed, leaving zero. The second request blocks until the
        # first commits, then re-reads the now-updated is_active
        # values, and sees the real remaining count.
        result = await db.execute(
            select(User.id)
            .where(User.role == ROLE_ADMIN, User.is_active == True)  # noqa: E712
            .with_for_update()
        )
        active_admin_ids = result.scalars().all()
        remaining = [admin_id for admin_id in active_admin_ids if admin_id != user_id]
        if len(remaining) == 0:
            raise CannotDeactivateLastAdminError(
                "Cannot deactivate the platform's only active admin."
            )

    user.is_active = is_active
    await db.flush()
    return user


async def update_user_role(user_id, role: str, current_user: User, db) -> User:
    """
    Changes a user's role, backing PATCH /admin/users/{id}/role.
    role is restricted to citizen/staff at the schema layer
    (UpdateUserRoleRequest), promoting to admin isn't possible here.

    Raises:
        UserNotFoundError: 404, if the user doesn't exist.
        CannotModifySelfError: 409, changing your own role is a
            self-lockout risk.
        CannotChangeAdminRoleError: 409, the platform has exactly one
            admin by design, this endpoint can't touch that account's role.
    """
    user = await db.get(User, user_id, options=[selectinload(User.department)])
    if user is None:
        raise UserNotFoundError("User not found.")

    if user.id == current_user.id:
        raise CannotModifySelfError("You cannot change your own role.")

    if user.role == ROLE_ADMIN:
        raise CannotChangeAdminRoleError(
            "Cannot change the admin account's role through this endpoint."
        )

    user.role = role
    await db.flush()
    return user


async def assign_staff_department(user_id, department: str | None, db) -> User:
    """
    Assigns (or, with department=None, unassigns) a staff member's
    department, backing PATCH /admin/users/{id}/department. department
    must be one of the fixed categories (enforced at the schema layer
    by AssignStaffDepartmentRequest's DepartmentCategory).

    Raises:
        UserNotFoundError: 404, if the user doesn't exist.
        UserNotStaffError: 409, if the user isn't a staff account,
            only officers belong to a department.
        DepartmentNotFoundError: 404, if department somehow doesn't
            match a real department, shouldn't happen in practice
            since these are seeded at startup (seed_departments).
    """
    user = await db.get(User, user_id, options=[selectinload(User.department)])
    if user is None:
        raise UserNotFoundError("User not found.")

    if user.role != ROLE_STAFF:
        raise UserNotStaffError("Only staff accounts can be assigned to a department.")

    if department is None:
        user.department = None
    else:
        department_result = await db.execute(select(Department).where(Department.name == department))
        department_row = department_result.scalar_one_or_none()
        if department_row is None:
            raise DepartmentNotFoundError("Department not found.")
        user.department = department_row

    await db.flush()
    return user
