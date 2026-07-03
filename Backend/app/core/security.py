"""
Security utilities for NAGRIK AI.

Responsibilities
----------------
- Password hashing
- Password verification
- JWT creation
- JWT verification
- OTP generation
- Secure random token generation
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

import secrets
import string
import hashlib
import hmac

# =====================================================
# Password Hashing
# =====================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

# =====================================================
# OAuth2
# =====================================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

# =====================================================
# JWT Constants
# =====================================================

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"

JWT_SUB = "sub"
JWT_ROLE = "role"
JWT_TYPE = "type"
JWT_EXP = "exp"

# =====================================================
# Password Utilities
# =====================================================


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    """
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    password_hash: str,
) -> bool:
    """
    Verify a plain-text password against its bcrypt hash.
    """
    return pwd_context.verify(
        plain_password,
        password_hash,
    )


# =====================================================
# JWT Utilities
# =====================================================


def _create_token(
    *,
    user_id: str,
    role: str,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    """
    Internal helper to create a JWT.
    """

    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        JWT_SUB: user_id,
        JWT_ROLE: role,
        JWT_TYPE: token_type,
        JWT_EXP: expire,
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_access_token(
    *,
    user_id: str,
    role: str,
) -> str:
    """
    Create an access token.
    """

    return _create_token(
        user_id=user_id,
        role=role,
        token_type=ACCESS_TOKEN,
        expires_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )


def create_refresh_token(
    *,
    user_id: str,
    role: str,
) -> str:
    """
    Create a refresh token.
    """

    return _create_token(
        user_id=user_id,
        role=role,
        token_type=REFRESH_TOKEN,
        expires_delta=timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    )


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    Raises:
        JWTError:
            If the token is invalid or expired.
    """

    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )


# =====================================================
# OTP Utilities
# =====================================================

def generate_otp(length: int = 6) -> str:
    """
    Generate a secure numeric OTP.
    """

    return "".join(
        secrets.choice(string.digits)
        for _ in range(length)
    )


# =====================================================
# Secure Random Tokens
# =====================================================


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Used for:
    - Email verification
    - Password reset
    - Future API tokens
    """

    return secrets.token_urlsafe(length)

# =====================================================
# OTP Hashing Utilities
# =====================================================

def hash_otp(otp: str) -> str:
    """
    Hash an OTP using HMAC-SHA256.

    Uses the application's SECRET_KEY as
    the HMAC secret.
    """

    return hmac.new(
        settings.OTP_SECRET_KEY.encode(),
        otp.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_otp_hash(
    otp: str,
    otp_hash: str,
) -> bool:
    """
    Verify an OTP against its stored hash.
    """

    return hmac.compare_digest(
        hash_otp(otp),
        otp_hash,
    )


