"""
Role-based authorization dependency.

Builds on get_current_user (app/dependencies/auth.py) to add a
second check: not just "is this a real, logged-in user" but
"is this user allowed to be here at all."

Usage in a route:

    from app.dependencies.roles import require_roles

    @router.get("/dashboard/officer")
    async def officer_dashboard(
        current_user: User = Depends(require_roles("officer")),
    ):
        ...

require_roles() is a dependency FACTORY — calling it returns the
actual dependency function, so each route can specify its own
allowed roles without needing a separate hand-written dependency
per role combination.
"""

from __future__ import annotations

from fastapi import Depends

from app.dependencies.auth import get_current_user
from app.model import User
from app.utils.exceptions import InsufficientPermissionsError


def require_roles(*allowed_roles: str):
    """
    Build a dependency that only allows the given roles through.

    Args:
        *allowed_roles: one or more role strings (see
            app/utils/constants.py — ROLE_CITIZEN, ROLE_STAFF,
            ROLE_ADMIN) that are permitted to access the route.

    Raises:
        InsufficientPermissionsError: 403 (AUTH_004), if the
            authenticated user's role is not in allowed_roles.

    Returns:
        A FastAPI dependency function resolving to the current
        User if — and only if — their role is permitted.
    """

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:

        if current_user.role not in allowed_roles:
            raise InsufficientPermissionsError(
                "You do not have permission to access this resource."
            )

        return current_user

    return _check_role