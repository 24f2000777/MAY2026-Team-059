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
from uuid import uuid4

# ── bcrypt / passlib compatibility ──────────────────────
# passlib 1.7.4 reads bcrypt.__about__.__version__, which was
# removed in bcrypt >= 4.1. This shim prevents the harmless
# but noisy "(trapped) error reading bcrypt version" warning
# on every startup. Must run before passlib is imported.
import bcrypt as _bcrypt

if not hasattr(_bcrypt, "__about__"):
    _bcrypt.__about__ = type(
        "_About", (), {"__version__": _bcrypt.__version__}
    )()

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer

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
# Bearer Token Scheme
# =====================================================
#
# HTTPBearer (not OAuth2PasswordBearer) because login is a
# plain JSON endpoint (LoginRequest), not an OAuth2 password
# grant form. HTTPBearer gives Swagger UI a simple "paste your
# token" field instead of a username/password form that would
# POST the wrong shape to /auth/login.

bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    description="Paste the access token returned by POST /auth/login.",
    auto_error=False,
)
# auto_error=False: by default HTTPBearer raises its own 403
# "Not authenticated" the instant the header is missing,
# bypassing our exception handlers entirely. That produces a
# 403 for "no token" while every other invalid-token case in
# this app correctly returns 401 — an inconsistent contract for
# API consumers. With auto_error=False, credentials is simply
# None when the header is absent, and get_current_token_payload
# (app/dependencies/auth.py) raises InvalidTokenError itself,
# giving a uniform 401 for every "not authenticated" case.

# =====================================================
# JWT Constants
# =====================================================

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"

JWT_SUB = "sub"
JWT_ROLE = "role"
JWT_TYPE = "type"
JWT_EXP = "exp"
JWT_JTI = "jti"

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


# A precomputed bcrypt hash of a password nobody will ever type,
# used only so that login_user can run a real bcrypt verification
# even when no user was found for the given email. bcrypt is
# deliberately slow (~100-300ms); skipping it entirely for unknown
# emails while performing it for known ones creates a measurable
# timing difference that lets an attacker distinguish "no such
# account" from "wrong password" without ever seeing the response
# body. Always doing the same bcrypt work regardless of whether
# the user exists closes that side channel.
DUMMY_PASSWORD_HASH = hash_password(
    "this-is-not-a-real-password-used-only-for-timing-safety"
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

    Every token gets a unique `jti` claim so that an
    individual token — as opposed to the whole user account —
    can be revoked independently. This is what makes a real
    logout possible: logout blacklists just this token's jti
    in Redis until it would have expired anyway.
    """

    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        JWT_SUB: user_id,
        JWT_ROLE: role,
        JWT_TYPE: token_type,
        JWT_EXP: expire,
        JWT_JTI: uuid4().hex,
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

    Uses the application's OTP_SECRET_KEY as
    the HMAC secret — a separate key from the
    JWT SECRET_KEY, so that OTP hashes and JWT
    signatures don't share a key.
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