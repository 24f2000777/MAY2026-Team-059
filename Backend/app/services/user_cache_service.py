"""
User Cache Service

get_current_user re-fetches the User row from the database on every
single authenticated request (see app/dependencies/auth.py), so that a
deactivated account, a role change, or a password change takes effect
immediately rather than waiting for the access token to expire. That's
the right behavior, but it means every request pays a full database
round trip just to re-confirm something that's usually unchanged since
the last request a few seconds ago.

This caches that row in Redis for a short TTL so most requests can skip
the database entirely. It is NOT meant to weaken the "changes take
effect immediately" guarantee: anywhere is_active, role, or
hashed_password actually changes (account activation, admin
deactivate/reactivate, role change, password change/reset) calls
invalidate_user_cache() itself, so the very next request after one of
those actions always re-fetches fresh from the database, regardless of
how much of the TTL is left. The TTL is only a backstop in case some
future code path changes one of those fields without remembering to
invalidate, not the actual mechanism keeping this safe.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from app.core.redis import redis_client
from app.model import User

CACHE_PREFIX = "user_cache"
TTL_SECONDS = 30

_FIELDS = (
    "id", "phone", "name", "email", "role", "hashed_password",
    "is_active", "department_id", "notification_email_enabled",
    "created_at", "updated_at",
)


def _redis_key(user_id) -> str:
    return f"{CACHE_PREFIX}:{user_id}"


async def get_cached_user(user_id) -> User | None:
    """
    Returns a User instance built from cached fields, or None on a
    cache miss. Deliberately NOT attached to any database session —
    safe for the read-only attribute access (current_user.role,
    current_user.is_active, etc.) every route already does, but must
    never be passed to db.add()/db.merge(), and its relationships
    (e.g. .complaints) must never be touched, they'd try to lazy-load
    against a session this instance was never attached to.
    """
    raw = await redis_client.get(_redis_key(user_id))
    if raw is None:
        return None

    data = json.loads(raw)
    data["id"] = uuid.UUID(data["id"])
    data["department_id"] = uuid.UUID(data["department_id"]) if data.get("department_id") else None
    data["created_at"] = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
    data["updated_at"] = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None

    return User(**data)


async def cache_user(user: User) -> None:
    """Caches the fields get_current_user needs, for TTL_SECONDS."""
    data = {
        "id": str(user.id),
        "phone": user.phone,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "hashed_password": user.hashed_password,
        "is_active": user.is_active,
        "department_id": str(user.department_id) if user.department_id else None,
        "notification_email_enabled": user.notification_email_enabled,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }
    await redis_client.setex(_redis_key(user.id), TTL_SECONDS, json.dumps(data))


async def invalidate_user_cache(user_id) -> None:
    """
    Clears a user's cached row immediately. Call this anywhere
    is_active, role, or hashed_password changes for a user, so the
    very next request after that change always sees the fresh value
    instead of a stale cached one.
    """
    await redis_client.delete(_redis_key(user_id))
