"""
One-time CLI bootstrap for the platform's single admin account.

There is no API path that can create an admin, deliberately, an
endpoint reachable over HTTP that mints a privileged account is an
attack surface this app doesn't want. This script is the only way an
admin account comes into existence, and it refuses to run a second
time (see _admin_already_exists below) so there's never more than one.

Usage (run from Backend/, with the venv active):

    python -m scripts.create_admin

Prompts for name, phone, email, and password, then writes the account
directly (already active, no OTP step, this is a trusted operator
running it, not a public signup).
"""

import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.model import User
from app.utils.constants import ROLE_ADMIN


async def _admin_already_exists(db) -> bool:
    result = await db.execute(select(User.id).where(User.role == ROLE_ADMIN))
    return result.first() is not None


async def _email_or_phone_taken(db, email: str, phone: str) -> str | None:
    result = await db.execute(
        select(User.email, User.phone).where((User.email == email) | (User.phone == phone))
    )
    row = result.first()
    if row is None:
        return None
    return "email" if row[0] == email else "phone"


_EMAIL_ADAPTER = TypeAdapter(EmailStr)


def _prompt(label: str, min_length: int, max_length: int) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if min_length <= len(value) <= max_length:
            return value
        print(f"  {label} must be {min_length}-{max_length} characters.")


def _prompt_email() -> str:
    while True:
        value = input("Email: ").strip()
        try:
            return _EMAIL_ADAPTER.validate_python(value)
        except ValidationError:
            print("  That doesn't look like a valid email address.")


def _prompt_password() -> str:
    while True:
        password = getpass.getpass("Password (min 8 characters): ")
        if len(password) < 8 or len(password) > 128:
            print("  Password must be 8-128 characters.")
            continue
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("  Passwords didn't match, try again.")
            continue
        return password


async def main() -> None:
    async with AsyncSessionLocal() as db:
        if await _admin_already_exists(db):
            print("An admin account already exists. Refusing to create a second one.")
            sys.exit(1)

        print("Creating the platform's single admin account.\n")
        name = _prompt("Name", 2, 100)
        phone = _prompt("Phone", 10, 15)
        email = _prompt_email()
        password = _prompt_password()

        conflict = await _email_or_phone_taken(db, email, phone)
        if conflict is not None:
            print(f"That {conflict} is already registered to another account.")
            sys.exit(1)

        admin = User(
            name=name,
            phone=phone,
            email=email,
            role=ROLE_ADMIN,
            hashed_password=hash_password(password),
            is_active=True,
        )
        db.add(admin)
        await db.commit()

        print(f"\nAdmin account created: {email}")


if __name__ == "__main__":
    asyncio.run(main())
