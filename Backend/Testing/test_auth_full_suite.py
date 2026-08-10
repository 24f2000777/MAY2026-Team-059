"""
Authentication Module — Full Feature & Edge Case Suite

Tests the ACTUAL HTTP layer (routes + dependencies + exception
handlers), not just the service functions directly — using
httpx against the real FastAPI app via ASGITransport. No
network socket, no running uvicorn process needed, but every
layer (Pydantic validation, get_current_user, blacklist,
global exception handlers) is exercised exactly as it would
be in production.

Prerequisites
-------------
- Postgres and Redis must be running and reachable per your
  .env (same as your other test scripts).
- httpx must be installed: pip install httpx

No real emails are sent: send_verification_email and
send_password_reset_email are monkeypatched to capture the
plaintext OTP in memory instead of calling smtplib, exactly
like test_auth_service_negative_auto.py.

Run once, fully unattended:

    python test_auth_full_suite.py
"""

from __future__ import annotations

import asyncio
import os
import sys

# This script now lives in Testing/, one level below Backend/,
# where the `app` package actually lives. Running a script from
# a subfolder only adds THAT subfolder to Python's import path,
# not the folder you invoked it from — so without this, every
# "from app..." import below would fail with
# ModuleNotFoundError: No module named 'app'. This line adds
# Backend/ (the parent of this file's folder) to the path,
# regardless of what directory you run the script from.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from uuid import uuid4

import httpx
import pytest
from jose import jwt as jose_jwt
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
# Email capture (no real emails sent)
# ==========================================================

CAPTURED_OTPS: dict[tuple[str, str], str] = {}


def _capture_verification_email(*, recipient: str, otp: str) -> None:
    CAPTURED_OTPS[(OTP_VERIFY_EMAIL, recipient)] = otp


def _capture_reset_email(*, recipient: str, otp: str) -> None:
    CAPTURED_OTPS[(OTP_RESET_PASSWORD, recipient)] = otp


@pytest.fixture(autouse=True, scope="module")
def _patch_email_sending():
    """
    Patches the names auth_service.py actually calls, scoped to just
    this module's test run and restored immediately after.

    This used to be two unconditional assignments at import time,
    with no teardown, permanently replacing the real
    send_verification_email/send_password_reset_email for the whole
    pytest process the moment this file was collected — collection
    happens for every file up front, before any test runs. Any other
    file collected in the same pytest invocation that does the same
    thing (new_test_auth_service_negative.py did, see its own
    _patch_email_sending fixture) would silently overwrite this
    file's patch with its own, so whichever file's patch ends up
    active when a given test actually runs decides which CAPTURED_OTPS
    dict the OTP lands in — a caller reading from the wrong one gets
    "RuntimeError: No OTP captured", even though every test here
    passes fine when this file runs alone.
    """
    original_verify = auth_service_module.send_verification_email
    original_reset = auth_service_module.send_password_reset_email

    auth_service_module.send_verification_email = _capture_verification_email
    auth_service_module.send_password_reset_email = _capture_reset_email

    yield

    auth_service_module.send_verification_email = original_verify
    auth_service_module.send_password_reset_email = original_reset


# ==========================================================
# Pytest fixture
# ==========================================================
#
# The `client` fixture every test function below takes now lives in
# Testing/conftest.py instead of here, once test_rbac_security.py
# needed to share it too — conftest.py fixtures are visible to every
# file under Testing/, a fixture defined inside one test module isn't.


def get_otp(purpose: str, email: str) -> str:
    key = (purpose, email)
    if key not in CAPTURED_OTPS:
        raise RuntimeError(f"No OTP captured for {key}")
    return CAPTURED_OTPS.pop(key)


# ==========================================================
# Test data helpers
# ==========================================================

DEFAULT_PASSWORD = "TestPass@123"
NEW_PASSWORD = "TestPass@456"


def unique_email() -> str:
    return f"auth_suite_{uuid4().hex[:10]}@example.com"


def unique_phone() -> str:
    return "9" + uuid4().hex[:9]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def craft_token(payload: dict) -> str:
    """
    Directly encode a JWT with the app's own secret, bypassing
    create_access_token/create_refresh_token, so we can build
    deliberately malformed tokens (missing sub, wrong type, etc).
    """

    return jose_jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


# ==========================================================
# Result Counters + Console Helpers
# ==========================================================

PASSED = 0
FAILED = 0


def title(text: str):
    print()
    print("=" * 70)
    print(text)
    print("=" * 70)


def passed(message: str):
    global PASSED
    PASSED += 1
    print(f"✅ {message}")


def failed(message: str):
    global FAILED
    FAILED += 1
    print(f"❌ {message}")


def expect_status(response: httpx.Response, expected: int, label: str) -> bool:
    if response.status_code == expected:
        passed(f"{label} -> {response.status_code} as expected")
        return True

    message = f"{label} -> expected {expected}, got {response.status_code}: {response.text}"
    failed(message)
    # Raise so pytest actually records this as a failure. Previously this
    # function only printed a red X and returned False, so under pytest
    # (once the fixture above made these collectible at all) every one of
    # these checks would silently "pass" regardless of the real response,
    # only an unrelated crash would ever fail a test.
    assert response.status_code == expected, message
    return False


def expect(condition: bool, success_msg: str, failure_msg: str):
    if condition:
        passed(success_msg)
    else:
        failed(failure_msg)
    assert condition, failure_msg


# ==========================================================
# Cleanup
# ==========================================================

async def cleanup(emails: list[str]):
    """
    Remove test users and any leftover OTP/captured state for
    the given emails. Safe to call even if the user or OTP
    never existed.
    """

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


async def api_get_me(client, token: str | None):
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


async def api_logout(client, token, refresh_token: str | None = None):
    body = {"refresh_token": refresh_token} if refresh_token else {}
    return await client.post("/auth/logout", json=body, headers=auth_headers(token))


# ==========================================================
# Fixture-style setup helpers
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
    Raises AssertionError if either step fails — used as setup,
    not as the thing under test.
    """

    email = email or unique_email()
    phone = phone or unique_phone()

    response = await api_register(client, email, phone, password, name)
    assert response.status_code == 201, f"setup register failed: {response.text}"

    otp = get_otp(OTP_VERIFY_EMAIL, email)
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
    Register + verify a user via the real API (which always
    creates citizens — there's no create-staff/admin endpoint
    yet, that belongs to the future Admin module), then directly
    overwrite the role column in the DB.

    This is a test-only shortcut to get an staff/admin account
    to test RBAC against, not something the real API supports.
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


async def login_get_tokens(client, email: str, password: str = DEFAULT_PASSWORD) -> tuple[str, str]:
    response = await api_login(client, email, password)
    assert response.status_code == 200, f"setup login failed: {response.text}"
    data = response.json()["data"]
    return data["access_token"], data["refresh_token"]


# ==========================================================
# REGISTER
# ==========================================================

async def test_register_success(client):
    title("REGISTER — success")
    email, phone = unique_email(), unique_phone()
    try:
        response = await api_register(client, email, phone)
        expect_status(response, 201, "Register new user")
    finally:
        await cleanup([email])


async def test_register_duplicate_verified_email(client):
    title("REGISTER — duplicate email (already verified)")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        response = await api_register(client, email, unique_phone())
        expect_status(response, 409, "Register with already-verified email")
    finally:
        await cleanup([email])


async def test_register_pending_duplicate_resends_otp(client):
    title("REGISTER — duplicate email (pending/unverified) resends OTP")
    email, phone = unique_email(), unique_phone()
    try:
        await api_register(client, email, phone)
        get_otp(OTP_VERIFY_EMAIL, email)  # consume first OTP

        response = await api_register(client, email, unique_phone())
        ok = expect_status(response, 201, "Re-register pending (unverified) email")

        if ok:
            expect(
                "pending" in response.json()["message"].lower(),
                "Response message indicates pending verification",
                f"Unexpected message: {response.json()['message']}",
            )
            expect(
                (OTP_VERIFY_EMAIL, email) in CAPTURED_OTPS,
                "A fresh OTP was sent on re-registration",
                "No new OTP was captured on re-registration",
            )
    finally:
        await cleanup([email])


async def test_register_duplicate_phone(client):
    title("REGISTER — duplicate phone")
    email_a, phone_a = unique_email(), unique_phone()
    email_b = unique_email()
    try:
        await create_verified_user(client, email=email_a, phone=phone_a)
        response = await api_register(client, email_b, phone_a)
        expect_status(response, 409, "Register with already-registered phone")
    finally:
        await cleanup([email_a, email_b])


# ==========================================================
# VERIFY OTP
# ==========================================================

async def test_verify_otp_wrong(client):
    title("VERIFY OTP — wrong code")
    email, phone = unique_email(), unique_phone()
    try:
        await api_register(client, email, phone)
        get_otp(OTP_VERIFY_EMAIL, email)
        response = await api_verify_otp(client, email, "000000")
        expect_status(response, 400, "Verify with wrong OTP")
    finally:
        await cleanup([email])


async def test_verify_otp_expired(client):
    title("VERIFY OTP — expired (deleted from Redis)")
    email, phone = unique_email(), unique_phone()
    try:
        await api_register(client, email, phone)
        get_otp(OTP_VERIFY_EMAIL, email)
        await redis_client.delete(f"{OTP_VERIFY_EMAIL}:{email}")
        response = await api_verify_otp(client, email, "123456")
        expect_status(response, 400, "Verify with expired OTP")
    finally:
        await cleanup([email])


async def test_verify_otp_already_verified(client):
    title("VERIFY OTP — already verified account")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        from app.services.otp_service import create_otp
        otp = await create_otp(email=email, purpose=OTP_VERIFY_EMAIL)
        response = await api_verify_otp(client, email, otp)
        expect_status(response, 409, "Verify an already-verified account")
    finally:
        await cleanup([email])


async def test_verify_otp_unknown_email(client):
    title("VERIFY OTP — unknown email")
    response = await api_verify_otp(client, "nobody_" + unique_email(), "123456")
    expect_status(response, 404, "Verify OTP for unregistered email")


async def test_verify_otp_success_returns_tokens(client):
    title("VERIFY OTP — success logs the user straight in")
    email, phone = unique_email(), unique_phone()
    try:
        await api_register(client, email, phone)
        otp = get_otp(OTP_VERIFY_EMAIL, email)
        response = await api_verify_otp(client, email, otp)
        expect_status(response, 200, "Verify with correct OTP")

        data = response.json()["data"]
        expect(
            bool(data and data.get("access_token") and data.get("refresh_token")),
            "Response includes a real access_token and refresh_token",
            f"Response did not include tokens: {response.text}",
        )
        expect(
            bool(data and data.get("user", {}).get("email") == email),
            "Response includes the verified user's own profile",
            f"Response user data missing/wrong: {response.text}",
        )

        # the returned access_token should actually work, not just be present
        me_response = await api_get_me(client, data["access_token"])
        expect_status(me_response, 200, "GET /auth/me with the token from verify-otp")
    finally:
        await cleanup([email])


async def test_resend_otp_for_pending_account(client):
    title("RESEND OTP — pending (unverified) account")
    email, phone = unique_email(), unique_phone()
    try:
        await api_register(client, email, phone)
        get_otp(OTP_VERIFY_EMAIL, email)  # consume the original

        response = await client.post("/auth/resend-otp", json={"email": email})
        expect_status(response, 200, "Resend OTP for a pending account")
        expect(
            (OTP_VERIFY_EMAIL, email) in CAPTURED_OTPS,
            "A fresh OTP was captured after resend",
            "No new OTP was captured after resend",
        )

        new_otp = get_otp(OTP_VERIFY_EMAIL, email)
        verify_response = await api_verify_otp(client, email, new_otp)
        expect_status(verify_response, 200, "Verify using the resent OTP")
    finally:
        await cleanup([email])


async def test_resend_otp_unknown_email(client):
    title("RESEND OTP — unknown email")
    response = await client.post("/auth/resend-otp", json={"email": "nobody_" + unique_email()})
    expect_status(response, 404, "Resend OTP for unregistered email")


async def test_resend_otp_already_verified(client):
    title("RESEND OTP — already verified account")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        response = await client.post("/auth/resend-otp", json={"email": email})
        expect_status(response, 409, "Resend OTP for an already-verified account")
    finally:
        await cleanup([email])


async def test_resend_otp_rate_limited(client):
    title("RESEND OTP — rate limited after 3 attempts per hour")
    email, phone = unique_email(), unique_phone()
    try:
        await api_register(client, email, phone)
        get_otp(OTP_VERIFY_EMAIL, email)  # drain the register-time OTP

        for attempt in range(1, 4):
            response = await client.post("/auth/resend-otp", json={"email": email})
            expect_status(
                response, 200, f"Resend-OTP attempt #{attempt} (within limit)"
            )
            get_otp(OTP_VERIFY_EMAIL, email)  # drain it so dict doesn't leak

        fourth_response = await client.post("/auth/resend-otp", json={"email": email})
        expect_status(
            fourth_response, 429, "4th resend-otp attempt within the hour"
        )
    finally:
        await cleanup([email])


async def test_verify_otp_rate_limited(client):
    title("VERIFY OTP — rate limited after 5 attempts per 15 minutes")
    email, phone = unique_email(), unique_phone()
    try:
        await api_register(client, email, phone)
        get_otp(OTP_VERIFY_EMAIL, email)  # drain it, we're guessing wrong on purpose

        for attempt in range(1, 6):
            response = await api_verify_otp(client, email, "000000")
            expect_status(
                response, 400, f"Wrong-OTP attempt #{attempt} (within limit)"
            )

        sixth_response = await api_verify_otp(client, email, "000000")
        expect_status(
            sixth_response, 429, "6th verify-otp attempt within the window"
        )
    finally:
        await cleanup([email])


# ==========================================================
# LOGIN
# ==========================================================

async def test_login_success(client):
    title("LOGIN — success")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        response = await api_login(client, email)
        ok = expect_status(response, 200, "Login with correct credentials")
        if ok:
            data = response.json()["data"]
            expect(
                "access_token" in data and "refresh_token" in data,
                "Response contains access and refresh tokens",
                f"Missing tokens in response: {data}",
            )
    finally:
        await cleanup([email])


async def test_login_wrong_password(client):
    title("LOGIN — wrong password")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        response = await api_login(client, email, password="WrongPass@999")
        expect_status(response, 401, "Login with wrong password")
    finally:
        await cleanup([email])


async def test_login_unknown_email(client):
    title("LOGIN — unknown email")
    response = await api_login(client, unique_email())
    expect_status(response, 401, "Login with unregistered email")


async def test_login_inactive_user(client):
    title("LOGIN — unverified (inactive) account")
    email, phone = unique_email(), unique_phone()
    try:
        await api_register(client, email, phone)
        response = await api_login(client, email)
        expect_status(response, 403, "Login before verifying email")
    finally:
        await cleanup([email])


# ==========================================================
# REFRESH
# ==========================================================

async def test_refresh_success(client):
    title("REFRESH — success")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        _, refresh_token = await login_get_tokens(client, email)
        response = await api_refresh(client, refresh_token)
        expect_status(response, 200, "Refresh with a valid refresh token")
    finally:
        await cleanup([email])


async def test_refresh_with_access_token(client):
    title("REFRESH — access token used as refresh token")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        access_token, _ = await login_get_tokens(client, email)
        response = await api_refresh(client, access_token)
        expect_status(response, 401, "Refresh using an access token")
    finally:
        await cleanup([email])


async def test_refresh_garbage_token(client):
    title("REFRESH — malformed token")
    response = await api_refresh(client, "this-is-not-a-jwt")
    expect_status(response, 401, "Refresh with a garbage string")


async def test_refresh_missing_sub(client):
    title("REFRESH — token missing 'sub' claim")
    token = craft_token({"role": "citizen", "type": "refresh"})
    response = await api_refresh(client, token)
    expect_status(response, 401, "Refresh with a token missing sub")


async def test_refresh_deleted_user(client):
    title("REFRESH — user deleted after token issued")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        _, refresh_token = await login_get_tokens(client, email)

        async with AsyncSessionLocal() as db:
            await db.execute(delete(User).where(User.email == email))
            await db.commit()

        response = await api_refresh(client, refresh_token)
        expect_status(response, 404, "Refresh after the user was deleted")
    finally:
        await cleanup([email])


async def test_refresh_rotates_token_old_one_rejected(client):
    title("REFRESH — rotates the refresh token; the old one is single-use")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        _, old_refresh_token = await login_get_tokens(client, email)

        first_response = await api_refresh(client, old_refresh_token)
        ok = expect_status(first_response, 200, "First refresh with the original token")

        if ok:
            new_refresh_token = first_response.json()["data"]["refresh_token"]

            expect(
                new_refresh_token != old_refresh_token,
                "A brand new refresh token was issued (rotation)",
                "Refresh token was NOT rotated — same token returned",
            )

            reuse_response = await api_refresh(client, old_refresh_token)
            expect_status(
                reuse_response, 401, "Reusing the OLD refresh token a second time"
            )

            second_response = await api_refresh(client, new_refresh_token)
            expect_status(
                second_response, 200, "The NEW refresh token works"
            )
    finally:
        await cleanup([email])


# ==========================================================
# FORGOT / RESET PASSWORD
# ==========================================================

async def test_forgot_password_unknown_user(client):
    title("FORGOT PASSWORD — unknown user")
    response = await api_forgot_password(client, unique_email())
    expect_status(response, 404, "Forgot password for unregistered email")


async def test_forgot_password_inactive_user(client):
    title("FORGOT PASSWORD — inactive (unverified) user")
    email, phone = unique_email(), unique_phone()
    try:
        await api_register(client, email, phone)
        response = await api_forgot_password(client, email)
        expect_status(response, 403, "Forgot password for unverified account")
    finally:
        await cleanup([email])


async def test_reset_password_wrong_otp(client):
    title("RESET PASSWORD — wrong OTP")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        await api_forgot_password(client, email)
        get_otp(OTP_RESET_PASSWORD, email)
        response = await api_reset_password(client, email, "000000", NEW_PASSWORD)
        expect_status(response, 400, "Reset password with wrong OTP")
    finally:
        await cleanup([email])


async def test_reset_password_expired_otp(client):
    title("RESET PASSWORD — expired OTP")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        await api_forgot_password(client, email)
        get_otp(OTP_RESET_PASSWORD, email)
        await redis_client.delete(f"{OTP_RESET_PASSWORD}:{email}")
        response = await api_reset_password(client, email, "123456", NEW_PASSWORD)
        expect_status(response, 400, "Reset password with expired OTP")
    finally:
        await cleanup([email])


async def test_reset_password_same_as_current(client):
    title("RESET PASSWORD — same as current password")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        await api_forgot_password(client, email)
        otp = get_otp(OTP_RESET_PASSWORD, email)
        response = await api_reset_password(client, email, otp, DEFAULT_PASSWORD)
        expect_status(response, 401, "Reset password to the same current password")
    finally:
        await cleanup([email])


async def test_reset_password_success_and_otp_not_reusable(client):
    title("RESET PASSWORD — success, then OTP reuse fails")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        await api_forgot_password(client, email)
        otp = get_otp(OTP_RESET_PASSWORD, email)

        response = await api_reset_password(client, email, otp, NEW_PASSWORD)
        ok = expect_status(response, 200, "Reset password with correct OTP")

        if ok:
            old_login = await api_login(client, email, DEFAULT_PASSWORD)
            expect(
                old_login.status_code == 401,
                "Old password no longer works after reset",
                f"Old password still works! status={old_login.status_code}",
            )

            new_login = await api_login(client, email, NEW_PASSWORD)
            expect(
                new_login.status_code == 200,
                "New password works after reset",
                f"New password rejected: {new_login.text}",
            )

        # Redundancy check: the same OTP must not work a second time,
        # since verify_otp deletes it from Redis on first success.
        reuse_response = await api_reset_password(client, email, otp, "AnotherPass@789")
        expect_status(reuse_response, 400, "Reuse the same reset OTP a second time")
    finally:
        await cleanup([email])


async def test_reset_otp_rate_limited(client):
    title("RESET PASSWORD — rate limited after 5 verify attempts per 15 minutes")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        await api_forgot_password(client, email)
        get_otp(OTP_RESET_PASSWORD, email)  # drain it, guessing wrong on purpose

        for attempt in range(1, 6):
            response = await api_reset_password(
                client, email, "000000", NEW_PASSWORD
            )
            expect_status(
                response, 400, f"Wrong-OTP reset attempt #{attempt} (within limit)"
            )

        sixth_response = await api_reset_password(
            client, email, "000000", NEW_PASSWORD
        )
        expect_status(
            sixth_response, 429, "6th reset-password attempt within the window"
        )
    finally:
        await cleanup([email])


async def test_forgot_password_rate_limited(client):
    title("FORGOT PASSWORD — rate limited after 3 attempts per hour")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)

        for attempt in range(1, 4):
            response = await api_forgot_password(client, email)
            expect_status(
                response, 200, f"Forgot-password attempt #{attempt} (within limit)"
            )
            get_otp(OTP_RESET_PASSWORD, email)  # drain it so dict doesn't leak

        fourth_response = await api_forgot_password(client, email)
        expect_status(
            fourth_response, 429, "4th forgot-password attempt within the hour"
        )
    finally:
        await cleanup([email])


# ==========================================================
# GET /auth/me
# ==========================================================

async def test_get_me_success(client):
    title("GET /auth/me — success")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        access_token, _ = await login_get_tokens(client, email)
        response = await api_get_me(client, access_token)
        ok = expect_status(response, 200, "Get own profile with a valid token")
        if ok:
            expect(
                response.json()["data"]["email"] == email,
                "Returned profile matches the logged-in user",
                f"Email mismatch: {response.json()}",
            )
    finally:
        await cleanup([email])


async def test_get_me_no_auth(client):
    title("GET /auth/me — no Authorization header")
    response = await api_get_me(client, None)
    expect_status(response, 401, "Get profile without a token")


async def test_get_me_garbage_token(client):
    title("GET /auth/me — malformed token")
    response = await api_get_me(client, "this-is-not-a-jwt")
    expect_status(response, 401, "Get profile with a garbage token")


# ==========================================================
# PUT /auth/me
# ==========================================================

async def test_update_me_name_and_phone(client):
    title("PUT /auth/me — update name and phone")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        access_token, _ = await login_get_tokens(client, email)

        new_phone = unique_phone()
        response = await api_update_me(
            client, access_token, name="Updated Name", phone=new_phone
        )
        ok = expect_status(response, 200, "Update own name and phone")
        if ok:
            data = response.json()["data"]
            expect(
                data["name"] == "Updated Name" and data["phone"] == new_phone,
                "Profile reflects the updated name and phone",
                f"Update did not apply: {data}",
            )
    finally:
        await cleanup([email])


async def test_update_me_noop(client):
    title("PUT /auth/me — empty body is a harmless no-op")
    email = unique_email()
    try:
        await create_verified_user(client, email=email, name="Original Name")
        access_token, _ = await login_get_tokens(client, email)

        response = await api_update_me(client, access_token)
        ok = expect_status(response, 200, "Update with no fields provided")
        if ok:
            expect(
                response.json()["data"]["name"] == "Original Name",
                "Name unchanged when no fields were provided",
                f"Name changed unexpectedly: {response.json()}",
            )
    finally:
        await cleanup([email])


async def test_update_me_duplicate_phone(client):
    title("PUT /auth/me — phone already taken by another user")
    email_a = unique_email()
    email_b, phone_b = unique_email(), unique_phone()
    try:
        await create_verified_user(client, email=email_a)
        await create_verified_user(client, email=email_b, phone=phone_b)

        access_token_a, _ = await login_get_tokens(client, email_a)
        response = await api_update_me(client, access_token_a, phone=phone_b)
        expect_status(response, 409, "Update phone to one already registered")
    finally:
        await cleanup([email_a, email_b])


async def test_update_me_no_auth(client):
    title("PUT /auth/me — no Authorization header")
    response = await client.put("/auth/me", json={"name": "Nobody"})
    expect_status(response, 401, "Update profile without a token")


# ==========================================================
# CHANGE PASSWORD
# ==========================================================

async def test_change_password_success(client):
    title("CHANGE PASSWORD — success")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        access_token, _ = await login_get_tokens(client, email)

        response = await api_change_password(
            client, access_token, DEFAULT_PASSWORD, NEW_PASSWORD
        )
        ok = expect_status(response, 200, "Change password with correct current password")

        if ok:
            old_login = await api_login(client, email, DEFAULT_PASSWORD)
            expect(
                old_login.status_code == 401,
                "Old password no longer works",
                f"Old password still works! status={old_login.status_code}",
            )

            new_login = await api_login(client, email, NEW_PASSWORD)
            expect(
                new_login.status_code == 200,
                "New password works",
                f"New password rejected: {new_login.text}",
            )
    finally:
        await cleanup([email])


async def test_change_password_wrong_current(client):
    title("CHANGE PASSWORD — wrong current password")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        access_token, _ = await login_get_tokens(client, email)
        response = await api_change_password(
            client, access_token, "TotallyWrong@000", NEW_PASSWORD
        )
        expect_status(response, 401, "Change password with wrong current password")
    finally:
        await cleanup([email])


async def test_change_password_same_as_current(client):
    title("CHANGE PASSWORD — new password same as current")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        access_token, _ = await login_get_tokens(client, email)
        response = await api_change_password(
            client, access_token, DEFAULT_PASSWORD, DEFAULT_PASSWORD
        )
        expect_status(response, 401, "Change password to the same password")
    finally:
        await cleanup([email])


async def test_change_password_no_auth(client):
    title("CHANGE PASSWORD — no Authorization header")
    response = await client.post(
        "/auth/change-password",
        json={"current_password": "x", "new_password": "y"},
    )
    expect_status(response, 401, "Change password without a token")


# ==========================================================
# LOGOUT
# ==========================================================

async def test_logout_revokes_access_token(client):
    title("LOGOUT — access token stops working immediately")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        access_token, _ = await login_get_tokens(client, email)

        logout_response = await api_logout(client, access_token)
        expect_status(logout_response, 200, "Logout with a valid access token")

        me_response = await api_get_me(client, access_token)
        expect_status(me_response, 401, "Reuse the same access token after logout")
    finally:
        await cleanup([email])


async def test_logout_revokes_refresh_token_if_provided(client):
    title("LOGOUT — refresh token revoked when provided")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        access_token, refresh_token = await login_get_tokens(client, email)

        await api_logout(client, access_token, refresh_token=refresh_token)

        refresh_response = await api_refresh(client, refresh_token)
        expect_status(
            refresh_response, 401, "Use the refresh token after logout revoked it"
        )
    finally:
        await cleanup([email])


async def test_logout_without_refresh_token_leaves_it_valid(client):
    title("LOGOUT — refresh token NOT provided stays valid (partial revocation)")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        access_token, refresh_token = await login_get_tokens(client, email)

        # Logout WITHOUT passing refresh_token in the body.
        await api_logout(client, access_token)

        refresh_response = await api_refresh(client, refresh_token)
        expect_status(
            refresh_response,
            200,
            "Refresh token still works (client chose not to revoke it)",
        )
    finally:
        await cleanup([email])


async def test_double_logout_second_call_rejected(client):
    title("LOGOUT — calling logout twice with the same token")
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        access_token, _ = await login_get_tokens(client, email)

        first = await api_logout(client, access_token)
        expect_status(first, 200, "First logout call")

        second = await api_logout(client, access_token)
        expect_status(
            second,
            401,
            "Second logout call with the now-revoked token",
        )
    finally:
        await cleanup([email])


async def test_logout_no_auth(client):
    title("LOGOUT — no Authorization header")
    response = await client.post("/auth/logout", json={})
    expect_status(response, 401, "Logout without a token")


# ==========================================================
# Main Runner
# ==========================================================
#
# A "DASHBOARD / RBAC" section lived here: 7 tests exercising
# GET /dashboard and /dashboard/{role}. Removed along with
# app/api/dashboard.py itself, that module was always placeholder
# content (per its own docstring) that never got replaced with real
# data, the real per-role dashboards ended up living at /complaints,
# /complaints/mine, /admin, and /analytics/summary instead, none of
# which the frontend ever reached through /dashboard/*. RBAC coverage
# for role gating itself lives on in test_rbac_security.py, repointed
# to real endpoints (GET /admin/departments, GET /ml/high-risk) the
# same way.

TESTS = [
    # Register
    test_register_success,
    test_register_duplicate_verified_email,
    test_register_pending_duplicate_resends_otp,
    test_register_duplicate_phone,
    # Verify OTP
    test_verify_otp_wrong,
    test_verify_otp_expired,
    test_verify_otp_already_verified,
    test_verify_otp_unknown_email,
    test_verify_otp_rate_limited,
    test_verify_otp_success_returns_tokens,
    # Resend OTP
    test_resend_otp_for_pending_account,
    test_resend_otp_unknown_email,
    test_resend_otp_already_verified,
    test_resend_otp_rate_limited,
    # Login
    test_login_success,
    test_login_wrong_password,
    test_login_unknown_email,
    test_login_inactive_user,
    # Refresh
    test_refresh_success,
    test_refresh_with_access_token,
    test_refresh_garbage_token,
    test_refresh_missing_sub,
    test_refresh_deleted_user,
    test_refresh_rotates_token_old_one_rejected,
    # Forgot / Reset Password
    test_forgot_password_unknown_user,
    test_forgot_password_inactive_user,
    test_reset_password_wrong_otp,
    test_reset_password_expired_otp,
    test_reset_password_same_as_current,
    test_reset_password_success_and_otp_not_reusable,
    test_reset_otp_rate_limited,
    test_forgot_password_rate_limited,
    # Get Profile
    test_get_me_success,
    test_get_me_no_auth,
    test_get_me_garbage_token,
    # Update Profile
    test_update_me_name_and_phone,
    test_update_me_noop,
    test_update_me_duplicate_phone,
    test_update_me_no_auth,
    # Change Password
    test_change_password_success,
    test_change_password_wrong_current,
    test_change_password_same_as_current,
    test_change_password_no_auth,
    # Logout
    test_logout_revokes_access_token,
    test_logout_revokes_refresh_token_if_provided,
    test_logout_without_refresh_token_leaves_it_valid,
    test_double_logout_second_call_rejected,
    test_logout_no_auth,
]


async def main():
    print()
    print("=" * 70)
    print("NAGRIK AI — FULL AUTHENTICATION SUITE (HTTP layer, no real email)")
    print("=" * 70)

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:

        for index, test in enumerate(TESTS, start=1):
            print()
            print(f"[{index}/{len(TESTS)}] {test.__name__}")

            try:
                await test(client)

            except Exception as exc:
                failed(f"{test.__name__} crashed")
                print(type(exc).__name__)
                print(exc)

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Passed : {PASSED}")
    print(f"Failed : {FAILED}")
    print()

    if FAILED == 0:
        print("🎉 ALL TESTS PASSED")
    else:
        print("⚠ Some tests failed.")

    print()

    await redis_client.aclose()


if __name__ == "__main__":
    # Running this file directly (not through pytest) never triggers
    # the _patch_email_sending fixture above, that only fires inside
    # a pytest session, so the patch has to be applied by hand here
    # for the standalone "python test_auth_full_suite.py" path this
    # file's own docstring documents.
    auth_service_module.send_verification_email = _capture_verification_email
    auth_service_module.send_password_reset_email = _capture_reset_email
    asyncio.run(main())