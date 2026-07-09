"""
Redis client configuration.

Provides a singleton Redis client for:

- OTP Storage
- Token Blacklist (logout)
- Rate Limiting
- Celery (once wired)

Uses redis.asyncio.Redis rather than the synchronous redis.Redis.
The synchronous client was being called directly from inside
async def routes/services (otp_service, token_blacklist_service,
rate_limit_service) — every one of those calls blocked the whole
event loop for its round-trip to Redis, meaning every other
concurrent request on the same worker had to wait behind it. This
matters most for is_token_blacklisted(), which runs on literally
every authenticated request. Switching to the async client and
awaiting every call fixes this without needing a thread pool or
any other workaround — redis-py 5.x's asyncio client speaks the
same Redis protocol, just non-blockingly.
"""

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings


redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


async def check_redis_connection() -> None:
    """
    Verify Redis connectivity.

    Raises:
        RuntimeError
            If Redis server is unavailable.
    """
    try:
        await redis_client.ping()

    except RedisError as exc:
        raise RuntimeError(
            "Redis server is unavailable."
        ) from exc