"""
Authentication dependencies.

Provides two reusable FastAPI dependencies:

    get_current_token_payload
        Decodes and validates the bearer access token —
        checks signature, expiry, token type, and that it
        hasn't been revoked via logout. Returns the raw JWT
        payload. Routes that only need the token itself
        (e.g. logout, which blacklists it) depend on this
        directly.

    get_current_user
        Builds on get_current_token_payload, additionally
        loading the User row the token belongs to. This is
        what protected routes normally depend on.

Usage in a route:

    from app.dependencies.auth import get_current_user

    @router.get("/auth/me")
    async def get_my_profile(
        current_user: User = Depends(get_current_user),
    ):
        ...

Usage where the raw token payload itself is needed (e.g. to
blacklist it on logout):

    from app.dependencies.auth import get_current_token_payload

    @router.post("/auth/logout")
    async def logout(
        payload: dict = Depends(get_current_token_payload),
    ):
        ...
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError
from jose.exceptions import ExpiredSignatureError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    bearer_scheme,
    decode_token,
    JWT_SUB,
    JWT_TYPE,
    JWT_JTI,
)

from app.model import User

from app.services.token_blacklist_service import is_token_blacklisted
from app.services.user_cache_service import cache_user, get_cached_user

from app.utils.constants import ACCESS_TOKEN

from app.utils.exceptions import (
    InvalidTokenError,
    UserNotFoundError,
    EmailNotVerifiedError,
)


async def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    Decode and validate the bearer access token.

    Checks, in order: that an Authorization header was even
    supplied, signature/expiry, that it is an access token
    (not a refresh token), and that it has not been revoked
    via logout.

    Raises:
        InvalidTokenError: 401, if the header is missing, or
            the token is malformed, expired, is a refresh
            token, or has been revoked.

    Returns:
        The decoded JWT payload dict.
    """

    if credentials is None:
        raise InvalidTokenError(
            "Not authenticated."
        )

    token = credentials.credentials

    try:
        payload = decode_token(token)

    except ExpiredSignatureError as exc:
        raise InvalidTokenError(
            "Access token has expired.",
            error_code="AUTH_002",
        ) from exc

    except JWTError as exc:
        raise InvalidTokenError(
            "Invalid access token.",
            error_code="AUTH_003",
        ) from exc

    # -------------------------------------------------
    # Must be an access token, not a refresh token
    # -------------------------------------------------

    if payload.get(JWT_TYPE) != ACCESS_TOKEN:
        raise InvalidTokenError(
            "Invalid access token."
        )

    # -------------------------------------------------
    # Revoked via logout?
    # -------------------------------------------------

    if await is_token_blacklisted(payload.get(JWT_JTI)):
        raise InvalidTokenError(
            "Access token has been revoked."
        )

    return payload


async def get_current_user(
    payload: dict = Depends(get_current_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the currently authenticated user from a validated
    bearer access token.

    The user's row (not just the JWT payload) is what actually
    decides whether this request goes through, so that a
    deactivated or deleted account immediately loses API access,
    without waiting for its token to expire. It's read from a
    short-lived Redis cache when available rather than the
    database on every single call — every place that actually
    changes is_active/role/hashed_password invalidates that cache
    immediately, so this doesn't weaken the "takes effect right
    away" guarantee, it just skips redundant database round trips
    for the (overwhelmingly common) case where nothing changed
    since the last request. See app/services/user_cache_service.py.

    Raises:
        InvalidTokenError: 401, if the token's user id claim
            is missing or malformed (signature/expiry/type/
            revocation are already checked by
            get_current_token_payload).
        UserNotFoundError: 404, if the token's user no longer
            exists.
        EmailNotVerifiedError: 403, if the account is inactive.

    Returns:
        The authenticated User ORM instance on a cache miss, or (on
        a cache hit, the common case) an equivalent but DETACHED
        instance built from cached fields, not attached to this
        request's db session — safe to read (current_user.role,
        current_user.is_active, etc.), but any route that needs to
        mutate the current user (update_profile, change_password)
        must re-fetch its own session-attached copy by id first,
        mutating current_user directly and flushing would silently
        no-op on a cache hit rather than persisting.
    """

    user_id = payload.get(JWT_SUB)

    if user_id is None:
        raise InvalidTokenError(
            "Invalid access token."
        )

    try:
        user_uuid = UUID(user_id)

    except (TypeError, ValueError) as exc:
        raise InvalidTokenError(
            "Invalid access token."
        ) from exc

    # -------------------------------------------------
    # Load user (cache first, database on a miss)
    # -------------------------------------------------

    user = await get_cached_user(user_uuid)

    if user is None:
        result = await db.execute(
            select(User).where(User.id == user_uuid)
        )

        user = result.scalar_one_or_none()

        if user is None:
            raise UserNotFoundError(
                "User not found."
            )

        await cache_user(user)

    # -------------------------------------------------
    # Account still active?
    # -------------------------------------------------

    if not user.is_active:
        raise EmailNotVerifiedError(
            "Account is not active."
        )

    return user