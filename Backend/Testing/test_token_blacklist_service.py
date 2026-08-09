"""
Pytest suite for app/services/token_blacklist_service.py: this is
what makes logout actually revoke a JWT before its natural expiry,
and what is_token_blacklisted() runs on every authenticated request
to check, so it's worth proving directly rather than only indirectly
through the auth suite's logout tests.

Hits real Redis, same reasoning as the other unmocked service suites
in this project.
"""

import time
import uuid

import pytest

from app.core.redis import redis_client
from app.services.token_blacklist_service import blacklist_token, is_token_blacklisted


def _unique_jti() -> str:
    return f"pytest-blacklist-{uuid.uuid4()}"


class TestBlacklistToken:
    async def test_a_blacklisted_token_is_reported_as_blacklisted(self):
        jti = _unique_jti()

        await blacklist_token(jti=jti, expires_at=int(time.time()) + 60)

        assert await is_token_blacklisted(jti) is True

        await redis_client.delete(f"blacklist_token:{jti}")

    async def test_is_a_noop_when_jti_is_missing(self):
        # Should not raise, and should not blacklist "None".
        await blacklist_token(jti=None, expires_at=int(time.time()) + 60)

    async def test_is_a_noop_when_expires_at_is_missing(self):
        jti = _unique_jti()

        await blacklist_token(jti=jti, expires_at=None)

        assert await is_token_blacklisted(jti) is False

    async def test_is_a_noop_for_an_already_expired_token(self):
        jti = _unique_jti()

        # expires_at in the past -> ttl_seconds <= 0, nothing to gain
        # by blacklisting a token that's already invalid on its own.
        await blacklist_token(jti=jti, expires_at=int(time.time()) - 60)

        assert await is_token_blacklisted(jti) is False

    async def test_ttl_matches_the_tokens_remaining_lifetime(self):
        jti = _unique_jti()

        await blacklist_token(jti=jti, expires_at=int(time.time()) + 120)

        ttl = await redis_client.ttl(f"blacklist_token:{jti}")

        assert 0 < ttl <= 120

        await redis_client.delete(f"blacklist_token:{jti}")


class TestIsTokenBlacklisted:
    async def test_a_never_blacklisted_token_is_not_blacklisted(self):
        assert await is_token_blacklisted(_unique_jti()) is False

    async def test_a_missing_jti_is_never_blacklisted(self):
        assert await is_token_blacklisted(None) is False
