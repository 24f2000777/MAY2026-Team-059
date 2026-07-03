"""
Redis client configuration.

Provides a singleton Redis client for:

- OTP Storage
- Caching
- Celery
- Notifications
"""

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


def check_redis_connection() -> None:
    """
    Verify Redis connectivity.

    Raises:
        RuntimeError
            If Redis server is unavailable.
    """
    try:
        redis_client.ping()

    except RedisError as exc:
        raise RuntimeError(
            "Redis server is unavailable."
        ) from exc