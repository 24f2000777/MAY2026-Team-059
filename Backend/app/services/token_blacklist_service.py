"""
Token Blacklist Service

Responsible for:

- Revoking a specific JWT (by its jti claim) before it
  would naturally expire
- Checking whether a given jti has been revoked

Used to implement real logout: since JWTs are stateless,
the only way to invalidate one before its expiry is to keep
a server-side record of "this specific token id is no longer
valid" and check that record on every authenticated request —
which is exactly why is_token_blacklisted() must be non-blocking:
it runs on every single authenticated request in the app.

Entries are stored in Redis with a TTL equal to the token's
remaining lifetime, so a blacklisted token's record disappears
by itself exactly when the token would have expired anyway —
no manual cleanup job needed, and the blacklist never grows
unbounded.
"""

from __future__ import annotations

import time

from app.core.redis import redis_client


BLACKLIST_PREFIX = "blacklist_token"


def _redis_key(jti: str) -> str:
    """
    Build the Redis key for a given token id.

    Example

        blacklist_token:3f9a1c2e4b8d4f6a9c0e1b2d3f4a5b6c
    """

    return f"{BLACKLIST_PREFIX}:{jti}"


async def blacklist_token(
    *,
    jti: str | None,
    expires_at: int | None,
) -> None:
    """
    Revoke a token by its jti until it would have expired.

    Args:
        jti: The token's unique id (JWT "jti" claim). Tokens
            issued before the jti claim existed have none —
            in that case there is nothing to key a blacklist
            entry on, so this is a no-op.
        expires_at: The token's "exp" claim (epoch seconds),
            used to size the Redis TTL so the entry expires
            at the same moment the token itself would have.
            Treated the same as a missing jti if absent.
    """

    if not jti or expires_at is None:
        return

    ttl_seconds = expires_at - int(time.time())

    if ttl_seconds <= 0:
        # Token is already expired on its own — nothing
        # gained by blacklisting it.
        return

    await redis_client.setex(
        _redis_key(jti),
        ttl_seconds,
        "1",
    )


async def is_token_blacklisted(jti: str | None) -> bool:
    """
    Check whether a token has been revoked.

    A token with no jti (issued before this claim existed)
    can never have been blacklisted, so it is always treated
    as not blacklisted rather than raising an error.

    Returns:
        bool
            True if the token has been revoked.
    """

    if not jti:
        return False

    return await redis_client.exists(_redis_key(jti)) == 1