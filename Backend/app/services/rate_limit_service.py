"""
Rate Limit Service

A generic, Redis-backed fixed-window rate limiter. Used for
password-reset requests (3/hour/email) and OTP verification
attempts (guards against brute-forcing a 6-digit code), and
written generically so any other action (e.g. login attempts)
can reuse it later with its own key, limit, and window.

Fixed-window counters are simpler than a sliding-window or
token-bucket approach and are accurate enough for this use
case: the goal is stopping abuse, not billing-grade precision.
"""

from __future__ import annotations

from app.core.redis import redis_client
from app.utils.exceptions import RateLimitExceededError


def _redis_key(scope: str, identifier: str) -> str:
    """
    Build the Redis key for a rate-limited action.

    Example

        rate_limit:forgot_password:amit@gmail.com
    """

    return f"rate_limit:{scope}:{identifier}"


async def enforce_rate_limit(
    *,
    scope: str,
    identifier: str,
    max_attempts: int,
    window_seconds: int,
) -> None:
    """
    Increment the attempt counter for (scope, identifier) and
    raise if it now exceeds max_attempts within window_seconds.

    The window starts on the first attempt and is fixed — it
    does not slide or reset early. Once window_seconds elapses
    since the first attempt, the counter expires from Redis and
    a fresh window begins on the next attempt.

    Raises:
        RateLimitExceededError: if this attempt is over the
            limit for the current window.
    """

    key = _redis_key(scope, identifier)

    attempts = await redis_client.incr(key)

    if attempts == 1:
        # First attempt in a fresh window — start the clock.
        await redis_client.expire(key, window_seconds)

    if attempts > max_attempts:
        raise RateLimitExceededError(
            f"Too many attempts. Please try again later."
        )