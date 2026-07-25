"""
Authentication Service Integration Test

This script tests the complete authentication
business layer without using the FastAPI routes.

Covered Flows
-------------
✓ Register
✓ Verify Email
✓ Login
✓ Refresh Token
✓ Forgot Password
✓ Reset Password

Requirements
------------
- PostgreSQL running
- Redis running
- SMTP configured
"""

from __future__ import annotations

import asyncio

from jose import JWTError
from sqlalchemy import delete, select

from app.model import User

from app.core.database import AsyncSessionLocal

from app.core.redis import redis_client

from app.core.security import (
    decode_token,
)

from app.services.auth_service import (
    register_user,
    verify_email,
    login_user,
    refresh_access_token,
    forgot_password,
    reset_password,
)

from app.services.otp_service import (
    create_otp,
)

from app.schemas.auth import (
    RegisterRequest,
    VerifyOTPRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

from app.utils.constants import (
    OTP_VERIFY_EMAIL,
    OTP_RESET_PASSWORD,
)

# =====================================================
# Test Configuration
# =====================================================

TEST_NAME = "ChatGPT Test User"

# TEST_EMAIL = "YOUR_EMAIL@gmail.com"
TEST_EMAIL = "21f3002439@ds.study.iitm.ac.in"

# TEST_PHONE = "9999999999"
TEST_PHONE = "9128286451"

TEST_PASSWORD = "Password@123"

NEW_PASSWORD = "Password@456"

# =====================================================
# Result Counters
# =====================================================

PASSED = 0

FAILED = 0


def passed(message: str):

    global PASSED

    PASSED += 1

    print(f"✅ {message}")


def failed(message: str):

    global FAILED

    FAILED += 1

    print(f"❌ {message}")


def title(text: str):

    print()
    print("=" * 70)
    print(text)
    print("=" * 70)


def prompt_otp(title_text: str) -> str:
    """
    Prompt the tester to enter the OTP
    received via email.
    """

    print()
    print("-" * 70)
    print(title_text)
    print("-" * 70)

    return input("Enter OTP: ").strip()

# =====================================================
# Cleanup
# =====================================================

async def cleanup():

    async with AsyncSessionLocal() as db:

        await db.execute(
            delete(User).where(
                User.email == TEST_EMAIL
            )
        )

        await db.commit()

    redis_client.delete(
        f"verify_email:{TEST_EMAIL}"
    )

    redis_client.delete(
        f"reset_password:{TEST_EMAIL}"
    )
    
    
# =====================================================
# Register User
# =====================================================

async def test_register():

    title("REGISTER USER")

    await cleanup()

    async with AsyncSessionLocal() as db:

        request = RegisterRequest(
            name=TEST_NAME,
            phone=TEST_PHONE,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )

        response = await register_user(
            db,
            request,
        )

        await db.commit()

        print(response.message)

        result = await db.execute(
            select(User).where(
                User.email == TEST_EMAIL
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            failed("User not created")
            return

        passed("User created")

        if user.is_active:
            failed("User should be inactive")
        else:
            passed("User inactive until email verification")

        if redis_client.exists(
            f"{OTP_VERIFY_EMAIL}:{TEST_EMAIL}"
        ):
            passed("Verification OTP stored in Redis")
        else:
            failed("Verification OTP missing from Redis")


# =====================================================
# Verify Email
# =====================================================

async def test_verify_email():

    title("VERIFY EMAIL")

    otp = prompt_otp(
        "Enter the OTP received after registration"
    )

    async with AsyncSessionLocal() as db:

        request = VerifyOTPRequest(
            email=TEST_EMAIL,
            otp=otp,
        )

        response = await verify_email(
            db,
            request,
        )

        await db.commit()

        print(response.message)

        result = await db.execute(
            select(User).where(
                User.email == TEST_EMAIL
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            failed("User not found")
            return

        if user.is_active:
            passed("Email verified")
        else:
            failed("Email verification failed")

        if redis_client.exists(
            f"{OTP_VERIFY_EMAIL}:{TEST_EMAIL}"
        ):
            failed("OTP still exists in Redis")
        else:
            passed("OTP removed from Redis")
            
            
            
# =====================================================
# Login
# =====================================================

async def test_login():

    title("LOGIN")

    async with AsyncSessionLocal() as db:

        request = LoginRequest(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )

        response = await login_user(
            db,
            request,
        )

        print("Access Token Generated")
        passed("Access token created")

        print("Refresh Token Generated")
        passed("Refresh token created")

        try:
            access_payload = decode_token(
                response.access_token,
            )

            refresh_payload = decode_token(
                response.refresh_token,
            )

            passed("Access token decoded")

            passed("Refresh token decoded")

        except JWTError:

            failed("JWT decoding failed")

            return

        if response.user.email == TEST_EMAIL:
            passed("Correct user returned")
        else:
            failed("Incorrect user returned")

        return response.refresh_token


# =====================================================
# Refresh Access Token
# =====================================================

async def test_refresh_token(
    refresh_token: str,
):

    title("REFRESH ACCESS TOKEN")

    async with AsyncSessionLocal() as db:

        response = await refresh_access_token(
            db,
            refresh_token,
        )

        print("New Access Token Generated")

        passed("Access token refreshed")

        try:

            payload = decode_token(
                response.access_token,
            )

            passed("New access token decoded")

        except JWTError:

            failed("New access token invalid")

            return

        if response.user.email == TEST_EMAIL:
            passed("Correct user returned")
        else:
            failed("Incorrect user returned")
            
            
# =====================================================
# Forgot Password
# =====================================================

async def test_forgot_password():

    title("FORGOT PASSWORD")

    async with AsyncSessionLocal() as db:

        request = ForgotPasswordRequest(
            email=TEST_EMAIL,
        )

        response = await forgot_password(
            db,
            request,
        )

        print(response.message)

        passed("Password reset email requested")

        if redis_client.exists(
            f"{OTP_RESET_PASSWORD}:{TEST_EMAIL}"
        ):
            passed("Reset OTP stored in Redis")
        else:
            failed("Reset OTP missing from Redis")


# =====================================================
# Reset Password
# =====================================================

async def test_reset_password():

    title("RESET PASSWORD")

    otp = prompt_otp(
        "Enter the Password Reset OTP received by email"
    )

    async with AsyncSessionLocal() as db:

        request = ResetPasswordRequest(
            email=TEST_EMAIL,
            otp=otp,
            new_password=NEW_PASSWORD,
        )

        response = await reset_password(
            db,
            request,
        )

        await db.commit()

        print(response.message)

        passed("Password reset successful")

        # ---------------------------------------------
        # Verify login with NEW password
        # ---------------------------------------------

        login_request = LoginRequest(
            email=TEST_EMAIL,
            password=NEW_PASSWORD,
        )

        login_response = await login_user(
            db,
            login_request,
        )

        if login_response.user.email == TEST_EMAIL:
            passed("Login with new password successful")
        else:
            failed("Unable to login with new password")

        # ---------------------------------------------
        # Old OTP removed?
        # ---------------------------------------------

        if redis_client.exists(
            f"{OTP_RESET_PASSWORD}:{TEST_EMAIL}"
        ):
            failed("Reset OTP still exists in Redis")
        else:
            passed("Reset OTP removed from Redis")
            
            
# =====================================================
# Main Test Runner
# =====================================================

async def main():

    print()

    print("=" * 70)
    print("NAGRIK AI AUTHENTICATION SERVICE TEST")
    print("=" * 70)

    try:

        await test_register()

        await test_verify_email()

        refresh_token = await test_login()

        await test_refresh_token(
            refresh_token,
        )

        await test_forgot_password()

        await test_reset_password()

    except Exception as exc:

        print()

        print("=" * 70)

        print("TEST FAILED")

        print("=" * 70)

        print(type(exc).__name__)

        print(exc)

        return

    print()

    print("=" * 70)

    print("RESULT")

    print("=" * 70)

    print(f"Passed : {PASSED}")

    print(f"Failed : {FAILED}")

    if FAILED == 0:

        print()

        print("🎉 ALL AUTHENTICATION TESTS PASSED")

    else:

        print()

        print("⚠ Some tests failed.")


if __name__ == "__main__":

    asyncio.run(main())