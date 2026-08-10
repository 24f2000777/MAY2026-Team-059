"""
Authentication Service Negative Tests (Fully Automated)

This is the same suite as test_auth_service_negative.py, but it
NEVER sends real emails and NEVER prompts for OTP input.

How it works
------------
auth_service.register_user() / forgot_password() eventually call:

    send_verification_email(recipient=..., otp=...)
    send_password_reset_email(recipient=..., otp=...)

These are looked up as globals inside the `app.services.auth_service`
module at call time. We overwrite those two names on the imported
module object with "capture" functions that just stash the plaintext
OTP in a dict instead of calling smtplib. The test functions then read
the OTP back out of that dict instead of asking a human to type it in.

Run once, it finishes on its own:

    python test_auth_service_negative_auto.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import random
from uuid import uuid4

# See test_auth_full_suite.py for why this line is needed now
# that this script lives in Testing/ instead of Backend/ directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from jose import jwt

from sqlalchemy import delete

from app.model import User

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client

# Import the auth_service MODULE itself (not just functions out of it),
# so we can monkeypatch the email-sending names it looks up internally.
import app.services.auth_service as auth_service_module

from app.schemas.auth import (
    RegisterRequest,
    VerifyOTPRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

from app.services.auth_service import (
    register_user,
    verify_email,
    login_user,
    refresh_access_token,
    forgot_password,
    reset_password,
)

from app.services.otp_service import create_otp

from app.utils.constants import (
    OTP_VERIFY_EMAIL,
    OTP_RESET_PASSWORD,
)

# ==========================================================
# Email capture (replaces real email sending)
# ==========================================================

# key = (purpose, email) -> plaintext OTP
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
    pytest process the moment this file was collected. Collection
    happens for every file up front, before any test runs, so any
    other file collected in the same pytest invocation (e.g.
    test_auth_full_suite.py, which relies on a real email actually
    being sent to read its OTP back out of the test inbox) would
    silently stop receiving real emails and fail across the board,
    even though each file passed fine on its own. Restoring the
    originals here means this module's patch can't leak into any
    other file's tests, and other collected modules are unaffected.
    """
    original_verify = auth_service_module.send_verification_email
    original_reset = auth_service_module.send_password_reset_email

    auth_service_module.send_verification_email = _capture_verification_email
    auth_service_module.send_password_reset_email = _capture_reset_email

    yield

    auth_service_module.send_verification_email = original_verify
    auth_service_module.send_password_reset_email = original_reset


def get_otp(purpose: str, email: str) -> str:
    """
    Fetch the OTP that was 'sent' for (purpose, email).

    Raises if nothing was captured, so failures are loud
    instead of hanging on input().
    """

    key = (purpose, email)

    if key not in CAPTURED_OTPS:
        raise RuntimeError(
            f"No OTP was captured for purpose={purpose!r} "
            f"email={email!r}. Did the send_* function change "
            f"its name/signature in auth_service.py?"
        )

    return CAPTURED_OTPS.pop(key)


# ==========================================================
# Test Configuration
# ==========================================================

class TestContext:
    """
    Stores reusable test data for the entire test suite.
    """

    def __init__(self):

        suffix = uuid4().hex[:8]

        self.name = "Negative Test User"

        self.email = f"negative_{suffix}@example.com"

        self.phone = (
            "9" + str(random.randint(100000000, 999999999))
        )

        self.password = "Password@123"
        self.new_password = "Password@456"

        # Reuse one verified account
        self.user_verified = False


ctx = TestContext()

# ==========================================================
# Result Counters
# ==========================================================

PASSED = 0
FAILED = 0

# ==========================================================
# Console Helpers
# ==========================================================


def title(text: str):
    print()
    print("=" * 70)
    print(text)
    print("=" * 70)


def subtitle(text: str):
    print()
    print("-" * 70)
    print(text)
    print("-" * 70)


def passed(message: str):
    global PASSED
    PASSED += 1
    print(f"✅ {message}")


def failed(message: str):
    global FAILED
    FAILED += 1
    print(f"❌ {message}")


async def cleanup():

    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == ctx.email))
        await db.commit()

    await redis_client.delete(f"{OTP_VERIFY_EMAIL}:{ctx.email}")
    await redis_client.delete(f"{OTP_RESET_PASSWORD}:{ctx.email}")

    # forgot_password is now rate-limited (3/hour/email). This
    # script reuses the same ctx.email across all 18 tests, so
    # without clearing the counter here, later tests that call
    # forgot_password would trip a limit meant to catch real
    # abuse, not repeated test runs against one fixed email.
    await redis_client.delete(f"rate_limit:forgot_password:{ctx.email}")

    # Same reasoning for the two OTP-verification-attempt
    # limiters added after a security review (guards against
    # brute-forcing a 6-digit OTP within its lifetime).
    await redis_client.delete(f"rate_limit:verify_otp_attempt:{ctx.email}")
    await redis_client.delete(f"rate_limit:reset_otp_attempt:{ctx.email}")

    # Drop any stale captured OTPs for this email too
    CAPTURED_OTPS.pop((OTP_VERIFY_EMAIL, ctx.email), None)
    CAPTURED_OTPS.pop((OTP_RESET_PASSWORD, ctx.email), None)

    # The user row was just wiped from the DB above, so the
    # "already verified" flag must be reset too — otherwise
    # create_verified_user() thinks a user still exists and
    # skips recreating it, causing every later test to fail
    # against a nonexistent user.
    ctx.user_verified = False


# ==========================================================
# Reusable User Setup
# ==========================================================

async def create_unverified_user():

    ctx.user_verified = False

    await cleanup()

    async with AsyncSessionLocal() as db:

        await register_user(
            db,
            RegisterRequest(
                name=ctx.name,
                phone=ctx.phone,
                email=ctx.email,
                password=ctx.password,
            ),
        )

        await db.commit()


async def create_verified_user():

    if ctx.user_verified:
        return

    await create_unverified_user()

    otp = get_otp(OTP_VERIFY_EMAIL, ctx.email)

    async with AsyncSessionLocal() as db:

        await verify_email(
            db,
            VerifyOTPRequest(email=ctx.email, otp=otp),
        )

        await db.commit()

    ctx.user_verified = True


async def login_test_user():

    async with AsyncSessionLocal() as db:

        return await login_user(
            db,
            LoginRequest(email=ctx.email, password=ctx.password),
        )


async def request_password_reset():

    async with AsyncSessionLocal() as db:

        await forgot_password(
            db,
            ForgotPasswordRequest(email=ctx.email),
        )

        await db.commit()


# ==========================================================
# Assertion Helper
# ==========================================================

async def expect_exception(title_text: str, operation):

    title(title_text)

    try:
        await operation()
        failed("Expected exception but operation succeeded.")

    except Exception as exc:
        print(type(exc).__name__)
        passed("Correct exception raised.")


# ==========================================================
# JWT Helper
# ==========================================================

def create_custom_refresh_token(payload: dict):
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ==========================================================
# Test Runner
# ==========================================================

async def run_test(test):

    try:
        await cleanup()
        await test()

    except Exception as exc:
        failed(f"{test.__name__} crashed")
        print(type(exc).__name__)
        print(exc)

    finally:
        await cleanup()


# ==========================================================
# Duplicate Email
# ==========================================================

async def test_duplicate_email():

    await create_verified_user()

    async with AsyncSessionLocal() as db:

        await expect_exception(
            "DUPLICATE EMAIL",
            lambda: register_user(
                db,
                RegisterRequest(
                    name="Another User",
                    phone="8888888888",
                    email=ctx.email,
                    password=ctx.password,
                ),
            ),
        )


# ==========================================================
# Duplicate Phone
# ==========================================================

async def test_duplicate_phone():

    await create_verified_user()

    async with AsyncSessionLocal() as db:

        await expect_exception(
            "DUPLICATE PHONE",
            lambda: register_user(
                db,
                RegisterRequest(
                    name="Another User",
                    phone=ctx.phone,
                    email=f"other_{uuid4().hex[:8]}@example.com",
                    password=ctx.password,
                ),
            ),
        )


# ==========================================================
# Wrong Verification OTP
# ==========================================================

async def test_wrong_verification_otp():

    await create_unverified_user()

    async with AsyncSessionLocal() as db:

        await expect_exception(
            "WRONG VERIFICATION OTP",
            lambda: verify_email(
                db,
                VerifyOTPRequest(email=ctx.email, otp="000000"),
            ),
        )


# ==========================================================
# Expired Verification OTP
# ==========================================================

async def test_expired_verification_otp():

    await create_unverified_user()

    await redis_client.delete(f"{OTP_VERIFY_EMAIL}:{ctx.email}")

    async with AsyncSessionLocal() as db:

        await expect_exception(
            "EXPIRED VERIFICATION OTP",
            lambda: verify_email(
                db,
                VerifyOTPRequest(email=ctx.email, otp="123456"),
            ),
        )


# ==========================================================
# Already Verified User
# ==========================================================

async def test_already_verified_user():

    await create_verified_user()

    otp = await create_otp(email=ctx.email, purpose=OTP_VERIFY_EMAIL)

    async with AsyncSessionLocal() as db:

        await expect_exception(
            "ALREADY VERIFIED USER",
            lambda: verify_email(
                db,
                VerifyOTPRequest(email=ctx.email, otp=otp),
            ),
        )


# ==========================================================
# Wrong Password
# ==========================================================

async def test_wrong_password():

    title("WRONG PASSWORD")

    await create_verified_user()

    async with AsyncSessionLocal() as db:

        try:
            await login_user(
                db,
                LoginRequest(email=ctx.email, password="WrongPassword@123"),
            )
            failed("Wrong password accepted")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Wrong password rejected")


# ==========================================================
# Unknown Email
# ==========================================================

async def test_unknown_email():

    title("UNKNOWN EMAIL")

    async with AsyncSessionLocal() as db:

        try:
            await login_user(
                db,
                LoginRequest(email="unknown@example.com", password=ctx.password),
            )
            failed("Unknown email accepted")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Unknown email rejected")


# ==========================================================
# Inactive User Login
# ==========================================================

async def test_inactive_user_login():

    title("INACTIVE USER LOGIN")

    await create_unverified_user()

    async with AsyncSessionLocal() as db:

        try:
            await login_user(
                db,
                LoginRequest(email=ctx.email, password=ctx.password),
            )
            failed("Inactive user logged in")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Inactive user rejected")


# ==========================================================
# Access Token Used As Refresh Token
# ==========================================================

async def test_access_token_as_refresh_token():

    title("ACCESS TOKEN AS REFRESH TOKEN")

    await create_verified_user()

    login_response = await login_test_user()

    async with AsyncSessionLocal() as db:

        try:
            await refresh_access_token(db, login_response.access_token)
            failed("Access token accepted as refresh token")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Access token rejected as refresh token")


# ==========================================================
# Invalid Refresh Token
# ==========================================================

async def test_invalid_refresh_token():

    title("INVALID REFRESH TOKEN")

    async with AsyncSessionLocal() as db:

        try:
            await refresh_access_token(db, "this-is-not-a-jwt")
            failed("Invalid JWT accepted")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Invalid JWT rejected")


# ==========================================================
# Deleted User Refresh Token
# ==========================================================

async def test_deleted_user_refresh_token():

    title("DELETED USER REFRESH TOKEN")

    await create_verified_user()

    login_response = await login_test_user()

    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == ctx.email))
        await db.commit()
        ctx.user_verified = False

    async with AsyncSessionLocal() as db:

        try:
            await refresh_access_token(db, login_response.refresh_token)
            failed("Deleted user refresh token accepted")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Deleted user rejected")


# ==========================================================
# Refresh Token Missing User ID
# ==========================================================

async def test_refresh_token_missing_sub():

    title("REFRESH TOKEN WITHOUT USER ID")

    token = create_custom_refresh_token({"role": "citizen", "type": "refresh"})

    async with AsyncSessionLocal() as db:

        try:
            await refresh_access_token(db, token)
            failed("JWT without sub accepted")

        except Exception as exc:
            print(type(exc).__name__)
            passed("JWT without sub rejected")


# ==========================================================
# Wrong Token Type
# ==========================================================

async def test_refresh_token_wrong_type():

    title("WRONG TOKEN TYPE")

    token = create_custom_refresh_token(
        {
            "sub": "12345678-1234-1234-1234-123456789012",
            "role": "citizen",
            "type": "access",
        }
    )

    async with AsyncSessionLocal() as db:

        try:
            await refresh_access_token(db, token)
            failed("Access token type accepted")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Wrong token type rejected")


# ==========================================================
# Forgot Password - Unknown User
# ==========================================================

async def test_forgot_password_unknown_user():

    title("FORGOT PASSWORD - UNKNOWN USER")

    async with AsyncSessionLocal() as db:

        try:
            await forgot_password(
                db, ForgotPasswordRequest(email="unknown@example.com")
            )
            failed("Forgot password accepted for unknown user")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Unknown user rejected")


# ==========================================================
# Forgot Password - Inactive User
# ==========================================================

async def test_forgot_password_inactive_user():

    title("FORGOT PASSWORD - INACTIVE USER")

    await create_unverified_user()

    async with AsyncSessionLocal() as db:

        try:
            await forgot_password(db, ForgotPasswordRequest(email=ctx.email))
            failed("Forgot password allowed for inactive user")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Inactive user rejected")


# ==========================================================
# Reset Password - Wrong OTP
# ==========================================================

async def test_reset_password_wrong_otp():

    title("RESET PASSWORD - WRONG OTP")

    await create_verified_user()
    await request_password_reset()

    async with AsyncSessionLocal() as db:

        try:
            await reset_password(
                db,
                ResetPasswordRequest(
                    email=ctx.email, otp="000000", new_password=ctx.new_password
                ),
            )
            failed("Wrong OTP accepted")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Wrong OTP rejected")


# ==========================================================
# Reset Password - Expired OTP
# ==========================================================

async def test_reset_password_expired_otp():

    title("RESET PASSWORD - EXPIRED OTP")

    await create_verified_user()
    await request_password_reset()

    await redis_client.delete(f"{OTP_RESET_PASSWORD}:{ctx.email}")

    async with AsyncSessionLocal() as db:

        try:
            await reset_password(
                db,
                ResetPasswordRequest(
                    email=ctx.email, otp="123456", new_password=ctx.new_password
                ),
            )
            failed("Expired OTP accepted")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Expired OTP rejected")


# ==========================================================
# Reset Password - Same Password
# ==========================================================

async def test_reset_password_same_password():

    title("RESET PASSWORD - SAME PASSWORD")

    await create_verified_user()
    await request_password_reset()

    otp = get_otp(OTP_RESET_PASSWORD, ctx.email)

    async with AsyncSessionLocal() as db:

        try:
            await reset_password(
                db,
                ResetPasswordRequest(
                    email=ctx.email, otp=otp, new_password=ctx.password
                ),
            )
            failed("Same password accepted")

        except Exception as exc:
            print(type(exc).__name__)
            passed("Same password rejected")


# ==========================================================
# Main Runner
# ==========================================================

TESTS = [
    # Registration
    test_duplicate_email,
    test_duplicate_phone,
    # Verification
    test_wrong_verification_otp,
    test_expired_verification_otp,
    test_already_verified_user,
    # Login
    test_wrong_password,
    test_unknown_email,
    test_inactive_user_login,
    # Refresh Token
    test_access_token_as_refresh_token,
    test_invalid_refresh_token,
    test_deleted_user_refresh_token,
    test_refresh_token_missing_sub,
    test_refresh_token_wrong_type,
    # Forgot Password
    test_forgot_password_unknown_user,
    test_forgot_password_inactive_user,
    # Reset Password
    test_reset_password_wrong_otp,
    test_reset_password_expired_otp,
    test_reset_password_same_password,
]


async def main():

    print()
    print("=" * 70)
    print("NAGRIK AI AUTHENTICATION NEGATIVE TESTS (AUTO / NO EMAIL)")
    print("=" * 70)

    await cleanup()

    for index, test in enumerate(TESTS, start=1):
        print()
        print(f"[{index}/{len(TESTS)}] {test.__name__}")
        await run_test(test)

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Passed : {PASSED}")
    print(f"Failed : {FAILED}")
    print()

    if FAILED == 0:
        print("🎉 ALL NEGATIVE TESTS PASSED")
    else:
        print("⚠ Some negative tests failed.")

    print()

    await cleanup()

    await redis_client.aclose()


if __name__ == "__main__":
    # Running this file directly (not through pytest) never triggers
    # the _patch_email_sending fixture above, that only fires inside
    # a pytest session, so the patch has to be applied by hand here
    # for the standalone CLI path this file's docstring documents.
    auth_service_module.send_verification_email = _capture_verification_email
    auth_service_module.send_password_reset_email = _capture_reset_email
    asyncio.run(main())