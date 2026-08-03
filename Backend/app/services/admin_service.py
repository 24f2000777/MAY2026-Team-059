"""
Admin-only staff account creation (POST /admin/users). The platform's
one admin account is never created here, or through any API route,
see scripts/create_admin.py for that.
"""

from sqlalchemy import select

from app.core.security import hash_password
from app.model import User
from app.utils.constants import ROLE_STAFF
from app.utils.exceptions import EmailAlreadyExistsError, PhoneAlreadyExistsError


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
