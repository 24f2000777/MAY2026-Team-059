"""
OTP Service

Responsible for

- Generate OTP
- Store hashed OTP in Redis
- Verify OTP
- Resend OTP
"""

from app.core.config import settings
from app.core.redis import redis_client
from app.core.security import (
    generate_otp,
    hash_otp,
    verify_otp_hash,
)


VERIFY_EMAIL_PREFIX = "verify_email"
RESET_PASSWORD_PREFIX = "reset_password"


def _redis_key(
    purpose: str,
    email: str,
) -> str:
    """
    Build Redis key.

    Example

        verify_email:amit@gmail.com

        reset_password:amit@gmail.com
    """

    return f"{purpose}:{email}"


def create_otp(
    *,
    email: str,
    purpose: str,
) -> str:
    """
    Generate a new OTP.

    The plain OTP is returned so that it can
    be sent via Email.

    Only the hashed OTP is stored in Redis.
    """

    otp = generate_otp()

    otp_hash = hash_otp(otp)

    redis_client.setex(
        _redis_key(
            purpose,
            email,
        ),
        settings.OTP_EXPIRE_SECONDS,
        otp_hash,
    )

    return otp


def verify_otp(
    *,
    email: str,
    otp: str,
    purpose: str,
) -> bool:
    """
    Verify OTP.

    Returns
    -------
    bool
        True if OTP is correct.
    """

    key = _redis_key(
        purpose,
        email,
    )

    stored_hash = redis_client.get(key)

    if stored_hash is None:
        return False

    if not verify_otp_hash(
        otp,
        stored_hash,
    ):
        return False

    redis_client.delete(key)

    return True


def resend_otp(
    *,
    email: str,
    purpose: str,
) -> str:
    """
    Generate and store a fresh OTP.

    Old OTP is removed automatically.
    """

    redis_client.delete(
        _redis_key(
            purpose,
            email,
        )
    )

    return create_otp(
        email=email,
        purpose=purpose,
    )


def delete_otp(
    *,
    email: str,
    purpose: str,
) -> None:
    """
    Delete OTP manually.

    Useful when an account is deleted
    before OTP verification.
    """

    redis_client.delete(
        _redis_key(
            purpose,
            email,
        )
    )