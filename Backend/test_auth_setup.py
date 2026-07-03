"""
Authentication Infrastructure Smoke Test

Run:

    python test_auth_setup.py

This script tests the authentication foundation
without touching production data.
"""

from uuid import uuid4

from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    hash_otp,
    verify_otp_hash,
)
from app.services.otp_service import (
    create_otp,
    verify_otp,
    resend_otp,
    delete_otp,
    VERIFY_EMAIL_PREFIX,
)

# Uncomment ONLY if you want to actually send an email.
# from app.services.email_service import send_verification_email

import asyncio


PASSED = 0
FAILED = 0


def success(msg):
    global PASSED
    PASSED += 1
    print(f"✅ {msg}")


def fail(msg):
    global FAILED
    FAILED += 1
    print(f"❌ {msg}")


def divider(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


async def test_database():
    divider("DATABASE")

    try:
        async with AsyncSessionLocal() as session:

            result = await session.execute(
                text("SELECT 1")
            )

            value = result.scalar()

            assert value == 1

            success("Database connection")

            tables = await session.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
                ORDER BY table_name
                """)
            )

            table_names = [row[0] for row in tables]

            print()

            print("Tables found:")

            for table in table_names:
                print("   •", table)

            success("Metadata loaded")

    except Exception as e:
        fail(e)


def test_redis():
    divider("REDIS")

    try:
        assert redis_client.ping()
        success("Redis connection")
    except Exception as e:
        fail(e)


def test_password_hashing():
    divider("PASSWORD HASHING")

    password = "StrongPassword@123"

    password_hash = hash_password(password)

    if verify_password(password, password_hash):
        success("Password verification")
    else:
        fail("Password verification")

    if not verify_password("WrongPassword", password_hash):
        success("Wrong password rejected")
    else:
        fail("Wrong password accepted")


def test_jwt():
    divider("JWT")

    user_id = str(uuid4())

    access = create_access_token(
        user_id=user_id,
        role="citizen",
    )

    refresh = create_refresh_token(
        user_id=user_id,
        role="citizen",
    )

    payload = decode_token(access)

    assert payload["sub"] == user_id
    assert payload["role"] == "citizen"

    success("Access token")

    payload = decode_token(refresh)

    assert payload["sub"] == user_id

    success("Refresh token")


def test_security_otp():
    divider("OTP UTILITIES")

    otp = generate_otp()

    print("Generated OTP :", otp)

    assert len(otp) == 6

    success("OTP generation")

    otp_hash = hash_otp(otp)

    if verify_otp_hash(otp, otp_hash):
        success("OTP hash verification")
    else:
        fail("OTP hash verification")


def test_redis_otp():
    divider("OTP SERVICE")

    email = "smoke_test@example.com"

    otp = create_otp(
        email=email,
        purpose=VERIFY_EMAIL_PREFIX,
    )

    print("Generated OTP :", otp)

    key = f"{VERIFY_EMAIL_PREFIX}:{email}"

    if redis_client.exists(key):
        success("OTP stored in Redis")
    else:
        fail("OTP not stored")

    ttl = redis_client.ttl(key)

    print("Redis TTL:", ttl)

    if ttl > 0:
        success("OTP expiry configured")
    else:
        fail("OTP expiry")

    if verify_otp(
        email=email,
        otp=otp,
        purpose=VERIFY_EMAIL_PREFIX,
    ):
        success("OTP verification")
    else:
        fail("OTP verification")

    if not redis_client.exists(key):
        success("OTP deleted after verification")
    else:
        fail("OTP not deleted")

    otp2 = resend_otp(
        email=email,
        purpose=VERIFY_EMAIL_PREFIX,
    )

    if otp2:
        success("OTP resend")
    else:
        fail("OTP resend")

    delete_otp(
        email=email,
        purpose=VERIFY_EMAIL_PREFIX,
    )

    success("OTP cleanup")


from app.services.email_service import send_verification_email


def test_otp_flow():

    divider("OTP FLOW TEST")

    email = "your_email@example.com"     # <- change this

    print("\nCreating OTP...")

    otp = create_otp(
        email=email,
        purpose=VERIFY_EMAIL_PREFIX,
    )

    success("OTP generated")

    print(f"\nOTP Generated: {otp}")

    print("\nSending Email...")

    send_verification_email(
        recipient=email,
        otp=otp,
    )

    success("Email sent")

    print(
        "\nCheck your Gmail inbox (or Spam folder)."
    )

    print("\nChecking Redis...")

    key = f"{VERIFY_EMAIL_PREFIX}:{email}"

    if redis_client.exists(key):
        success("OTP stored in Redis")
    else:
        fail("OTP not stored")

    ttl = redis_client.ttl(key)

    print(f"\nRedis TTL: {ttl} seconds")

    if ttl > 0:
        success("OTP expiry configured")
    else:
        fail("TTL missing")

    print("\nVerifying OTP...")

    if verify_otp(
        email=email,
        otp=otp,
        purpose=VERIFY_EMAIL_PREFIX,
    ):
        success("OTP verified")
    else:
        fail("OTP verification failed")

    print("\nChecking Redis cleanup...")

    if not redis_client.exists(key):
        success("OTP deleted")
    else:
        fail("OTP still exists")



# Uncomment if you want to send a real email.
#
# def test_email():
#
#     divider("EMAIL")
#
#     send_verification_email(
#         recipient="YOUR_EMAIL@gmail.com",
#         otp="123456",
#     )
#
#     success("Email sent")


async def main():

    print("\n")
    print("=" * 70)
    print("NAGRIK AI AUTHENTICATION FOUNDATION TEST")
    print("=" * 70)

    print("\nEnvironment:", settings.ENVIRONMENT)

    await test_database()

    test_redis()

    test_password_hashing()

    test_jwt()

    test_otp_flow()

    # test_email()

    print("\n")
    print("=" * 70)

    print("RESULT")

    print("=" * 70)

    print(f"Passed : {PASSED}")
    print(f"Failed : {FAILED}")

    if FAILED == 0:
        print("\n🎉 ALL TESTS PASSED")
    else:
        print("\n⚠️ SOME TESTS FAILED")


if __name__ == "__main__":
    asyncio.run(main())