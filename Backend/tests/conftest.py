"""
Shared pytest fixtures for the NAGRIK AI backend test suite.

This file is the foundation that all other test files build on.
It provides:

    - ``client``            — httpx.AsyncClient wired to the FastAPI app
    - ``mock_email``        — auto-used; captures OTPs instead of sending emails
    - ``get_captured_otp``  — helper to retrieve a captured OTP
    - ``create_test_user``  — factory fixture to register + verify a user
    - ``citizen_user``      — a logged-in citizen  (dict with user info + token)
    - ``staff_user``        — a logged-in staff member
    - ``admin_user``        — a logged-in admin

Usage in a test file:

    async def test_something(client, citizen_user):
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {citizen_user['access_token']}"},
        )
        assert response.status_code == 200
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.main import app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client
from app.model import User

import app.services.auth_service as auth_service_module

from app.utils.constants import (
    OTP_VERIFY_EMAIL,
    OTP_RESET_PASSWORD,
    ROLE_CITIZEN,
    ROLE_STAFF,
    ROLE_ADMIN,
)


# ==========================================================
# Constants
# ==========================================================

DEFAULT_PASSWORD = "TestPass@123"


# ==========================================================
# Email capture — no real emails are ever sent
# ==========================================================

CAPTURED_OTPS: dict[tuple[str, str], str] = {}


def _capture_verification_email(*, recipient: str, otp: str) -> None:
    CAPTURED_OTPS[(OTP_VERIFY_EMAIL, recipient)] = otp


def _capture_reset_email(*, recipient: str, otp: str) -> None:
    CAPTURED_OTPS[(OTP_RESET_PASSWORD, recipient)] = otp


# Monkeypatch at module load time (same strategy the old suite
# used) — this is simpler and avoids scope/ordering issues with
# pytest's monkeypatch fixture vs async fixture setup.
auth_service_module.send_verification_email = _capture_verification_email
auth_service_module.send_password_reset_email = _capture_reset_email


# ==========================================================
# Fixtures
# ==========================================================


@pytest.fixture(scope="session")
def event_loop():
    """
    Override the default event_loop fixture to use session scope.

    The SQLAlchemy async engine and Redis client are module-level
    singletons created during import, so they are bound to the
    first event loop that touches them. pytest-asyncio 0.23
    defaults to creating a NEW loop per test function, which
    causes asyncpg "another operation is in progress" errors
    because the pooled connections belong to a different loop.

    By sharing a single loop across the entire session, all tests
    and the ASGI app use the same loop — matching how the old
    custom runner worked (asyncio.run(main())).
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def client():
    """
    Provide an httpx.AsyncClient wired to the FastAPI app via
    ASGITransport. No real network socket or running uvicorn
    process is needed, but every layer (Pydantic validation,
    dependencies, exception handlers) is exercised exactly as
    it would be in production.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as c:
        yield c



# ==========================================================
# OTP Helpers
# ==========================================================


def get_captured_otp(purpose: str, email: str) -> str:
    """Retrieve a captured OTP. Raises RuntimeError if missing."""
    key = (purpose, email)
    if key not in CAPTURED_OTPS:
        raise RuntimeError(f"No OTP captured for {key}")
    return CAPTURED_OTPS.pop(key)


# ==========================================================
# Test data helpers
# ==========================================================


def unique_email() -> str:
    return f"pytest_{uuid4().hex[:10]}@example.com"


def unique_phone() -> str:
    return "9" + uuid4().hex[:9]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==========================================================
# API call wrappers
# ==========================================================


async def api_register(client, email, phone, password=DEFAULT_PASSWORD, name="Test User"):
    return await client.post(
        "/auth/register",
        json={"name": name, "phone": phone, "email": email, "password": password},
    )


async def api_verify_otp(client, email, otp):
    return await client.post("/auth/verify-otp", json={"email": email, "otp": otp})


async def api_login(client, email, password=DEFAULT_PASSWORD):
    return await client.post("/auth/login", json={"email": email, "password": password})


async def api_refresh(client, refresh_token):
    return await client.post("/auth/refresh", json={"refresh_token": refresh_token})


async def api_forgot_password(client, email):
    return await client.post("/auth/forgot-password", json={"email": email})


async def api_reset_password(client, email, otp, new_password):
    return await client.post(
        "/auth/reset-password",
        json={"email": email, "otp": otp, "new_password": new_password},
    )


async def api_get_me(client, token):
    headers = auth_headers(token) if token else {}
    return await client.get("/auth/me", headers=headers)


async def api_update_me(client, token, **fields):
    return await client.put("/auth/me", json=fields, headers=auth_headers(token))


async def api_change_password(client, token, current_password, new_password):
    return await client.post(
        "/auth/change-password",
        json={"current_password": current_password, "new_password": new_password},
        headers=auth_headers(token),
    )


async def api_logout(client, token, refresh_token=None):
    body = {"refresh_token": refresh_token} if refresh_token else {}
    return await client.post("/auth/logout", json=body, headers=auth_headers(token))


# ==========================================================
# User creation helpers
# ==========================================================


async def create_verified_user(
    client,
    email: str | None = None,
    phone: str | None = None,
    password: str = DEFAULT_PASSWORD,
    name: str = "Test User",
) -> tuple[str, str]:
    """
    Register + verify a brand new user. Returns (email, phone).
    """
    email = email or unique_email()
    phone = phone or unique_phone()

    response = await api_register(client, email, phone, password, name)
    assert response.status_code == 201, f"setup register failed: {response.text}"

    otp = get_captured_otp(OTP_VERIFY_EMAIL, email)
    response = await api_verify_otp(client, email, otp)
    assert response.status_code == 200, f"setup verify failed: {response.text}"

    return email, phone


async def create_verified_user_with_role(
    client,
    role: str,
    email: str | None = None,
    phone: str | None = None,
    password: str = DEFAULT_PASSWORD,
    name: str = "Test User",
) -> tuple[str, str]:
    """
    Register + verify a user, then directly overwrite the role
    column in the DB (test-only shortcut — no create-staff/admin
    endpoint exists yet).
    """
    email, phone = await create_verified_user(
        client, email=email, phone=phone, password=password, name=name
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.role = role
        await db.commit()

    return email, phone


async def login_get_tokens(client, email, password=DEFAULT_PASSWORD) -> tuple[str, str]:
    """Login and return (access_token, refresh_token)."""
    response = await api_login(client, email, password)
    assert response.status_code == 200, f"setup login failed: {response.text}"
    data = response.json()["data"]
    return data["access_token"], data["refresh_token"]


# ==========================================================
# Cleanup
# ==========================================================


async def cleanup(emails: list[str]):
    """
    Remove test users and any leftover OTP/captured state.
    Safe to call even if the user never existed.
    """
    # Yield control so any pending asyncpg rollbacks from ASGI
    # error-path responses can complete before we touch the pool.
    await asyncio.sleep(0.05)

    async with AsyncSessionLocal() as db:
        for email in emails:
            await db.execute(delete(User).where(User.email == email))
        await db.commit()

    for email in emails:
        await redis_client.delete(f"{OTP_VERIFY_EMAIL}:{email}")
        await redis_client.delete(f"{OTP_RESET_PASSWORD}:{email}")
        CAPTURED_OTPS.pop((OTP_VERIFY_EMAIL, email), None)
        CAPTURED_OTPS.pop((OTP_RESET_PASSWORD, email), None)


# ==========================================================
# Sample user fixtures (citizen / staff / admin)
# ==========================================================


@pytest_asyncio.fixture
async def citizen_user(client):
    """
    Yields a dict with keys: email, phone, access_token,
    refresh_token, role. The user is cleaned up after the test.
    """
    email, phone = await create_verified_user(client)
    access_token, refresh_token = await login_get_tokens(client, email)
    yield {
        "email": email,
        "phone": phone,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": ROLE_CITIZEN,
    }
    await cleanup([email])


@pytest_asyncio.fixture
async def staff_user(client):
    """
    Yields a logged-in staff user dict with keys: email, phone,
    access_token, refresh_token, role.
    """
    email, phone = await create_verified_user_with_role(client, ROLE_STAFF)
    access_token, refresh_token = await login_get_tokens(client, email)
    yield {
        "email": email,
        "phone": phone,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": ROLE_STAFF,
    }
    await cleanup([email])


@pytest_asyncio.fixture
async def admin_user(client):
    """
    Yields a logged-in admin user dict with keys: email, phone,
    access_token, refresh_token, role.
    """
    email, phone = await create_verified_user_with_role(client, ROLE_ADMIN)
    access_token, refresh_token = await login_get_tokens(client, email)
    yield {
        "email": email,
        "phone": phone,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": ROLE_ADMIN,
    }
    await cleanup([email])
