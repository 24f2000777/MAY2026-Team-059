"""
Pytest suite for app/services/otp_service.py: generating, storing,
verifying, resending, and deleting OTPs.

Hits real Redis, same reasoning as the other unmocked service suites
in this project — this is exactly the module that guards account
verification and password reset, worth proving for real rather than
against a mock.
"""

import uuid

import pytest

from app.core.redis import redis_client
from app.services.otp_service import create_otp, delete_otp, resend_otp, verify_otp

PURPOSE = "verify_email"


def _unique_email() -> str:
    return f"pytest-otp-service-{uuid.uuid4()}@example.com"


@pytest.fixture
async def email():
    addr = _unique_email()
    yield addr
    # Belt-and-suspenders cleanup in case a test fails before its own
    # delete_otp/verify_otp call would have removed the key.
    await redis_client.delete(f"{PURPOSE}:{addr}")


class TestCreateOtp:
    async def test_creates_a_verifiable_otp(self, email):
        otp = await create_otp(email=email, purpose=PURPOSE)

        assert len(otp) == 6
        assert otp.isdigit()
        assert await verify_otp(email=email, otp=otp, purpose=PURPOSE) is True

    async def test_stores_only_the_hash_not_the_plain_otp(self, email):
        otp = await create_otp(email=email, purpose=PURPOSE)

        stored = await redis_client.get(f"{PURPOSE}:{email}")

        assert stored != otp
        assert otp not in stored


class TestVerifyOtp:
    async def test_rejects_a_wrong_otp(self, email):
        await create_otp(email=email, purpose=PURPOSE)

        assert await verify_otp(email=email, otp="000000", purpose=PURPOSE) is False

    async def test_rejects_when_no_otp_was_ever_created(self, email):
        assert await verify_otp(email=email, otp="123456", purpose=PURPOSE) is False

    async def test_a_correct_otp_can_only_be_used_once(self, email):
        otp = await create_otp(email=email, purpose=PURPOSE)

        assert await verify_otp(email=email, otp=otp, purpose=PURPOSE) is True
        assert await verify_otp(email=email, otp=otp, purpose=PURPOSE) is False

    async def test_purposes_are_isolated(self, email):
        otp = await create_otp(email=email, purpose=PURPOSE)

        assert await verify_otp(email=email, otp=otp, purpose="reset_password") is False

        await delete_otp(email=email, purpose=PURPOSE)


class TestResendOtp:
    async def test_invalidates_the_previous_otp(self, email):
        first = await create_otp(email=email, purpose=PURPOSE)
        second = await resend_otp(email=email, purpose=PURPOSE)

        assert first != second
        assert await verify_otp(email=email, otp=first, purpose=PURPOSE) is False
        assert await verify_otp(email=email, otp=second, purpose=PURPOSE) is True


class TestDeleteOtp:
    async def test_a_deleted_otp_no_longer_verifies(self, email):
        otp = await create_otp(email=email, purpose=PURPOSE)

        await delete_otp(email=email, purpose=PURPOSE)

        assert await verify_otp(email=email, otp=otp, purpose=PURPOSE) is False

    async def test_deleting_a_nonexistent_otp_does_not_raise(self, email):
        await delete_otp(email=email, purpose=PURPOSE)
