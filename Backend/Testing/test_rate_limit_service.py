"""
Pytest suite for app/services/rate_limit_service.py, the generic
fixed-window limiter behind login, OTP verify/resend, and
password-reset requests. Worth proving directly since a bug here
either locks legitimate users out or lets brute-forcing through
silently, neither of which the endpoints that call it would
obviously surface as a test failure of their own.

Hits real Redis, same reasoning as the other unmocked service suites
in this project.
"""

import uuid

import pytest

from app.core.redis import redis_client
from app.services.rate_limit_service import enforce_rate_limit
from app.utils.exceptions import RateLimitExceededError


def _unique_identifier() -> str:
    return f"pytest-rate-limit-{uuid.uuid4()}@example.com"


@pytest.fixture
async def identifier():
    ident = _unique_identifier()
    yield ident
    await redis_client.delete(f"rate_limit:pytest_scope:{ident}")


class TestEnforceRateLimit:
    async def test_allows_attempts_within_the_limit(self, identifier):
        for _ in range(3):
            await enforce_rate_limit(
                scope="pytest_scope", identifier=identifier, max_attempts=3, window_seconds=60
            )
        # No exception raised across all 3 allowed attempts.

    async def test_rejects_the_attempt_that_exceeds_the_limit(self, identifier):
        for _ in range(3):
            await enforce_rate_limit(
                scope="pytest_scope", identifier=identifier, max_attempts=3, window_seconds=60
            )

        with pytest.raises(RateLimitExceededError):
            await enforce_rate_limit(
                scope="pytest_scope", identifier=identifier, max_attempts=3, window_seconds=60
            )

    async def test_scopes_are_isolated(self, identifier):
        for _ in range(3):
            await enforce_rate_limit(
                scope="pytest_scope", identifier=identifier, max_attempts=3, window_seconds=60
            )

        # A different scope for the same identifier has its own,
        # unexhausted counter.
        await enforce_rate_limit(
            scope="pytest_other_scope", identifier=identifier, max_attempts=3, window_seconds=60
        )

        await redis_client.delete(f"rate_limit:pytest_other_scope:{identifier}")

    async def test_identifiers_are_isolated(self):
        a = _unique_identifier()
        b = _unique_identifier()

        for _ in range(3):
            await enforce_rate_limit(scope="pytest_scope", identifier=a, max_attempts=3, window_seconds=60)

        # b's counter is untouched by a's attempts.
        await enforce_rate_limit(scope="pytest_scope", identifier=b, max_attempts=3, window_seconds=60)

        await redis_client.delete(f"rate_limit:pytest_scope:{a}")
        await redis_client.delete(f"rate_limit:pytest_scope:{b}")

    async def test_first_attempt_starts_a_ttl_on_the_window(self, identifier):
        await enforce_rate_limit(
            scope="pytest_scope", identifier=identifier, max_attempts=5, window_seconds=60
        )

        ttl = await redis_client.ttl(f"rate_limit:pytest_scope:{identifier}")

        assert 0 < ttl <= 60
