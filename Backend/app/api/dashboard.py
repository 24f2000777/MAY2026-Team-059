"""
Dashboard routes.

These are intentionally placeholders. Their job right now is
to prove role-based routing works end-to-end (a citizen really
can't reach the officer dashboard, etc.) — the Complaint/
Officer/Admin modules will replace the placeholder content with
real data (open complaints, assigned work, analytics, ...) once
those APIs exist.

GET /dashboard needs no specific role beyond being logged in —
it exists so a frontend can call ONE endpoint right after login
and get told which role-specific dashboard to route to, instead
of hardcoding that mapping on the client.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_roles
from app.model import User
from app.schemas.common import SuccessResponse
from app.utils.constants import ROLE_ADMIN, ROLE_CITIZEN, ROLE_OFFICER


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "",
    response_model=SuccessResponse[dict],
    summary="Get the dashboard route for the current user's role",
)
async def get_my_dashboard(
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[dict]:
    """
    Tell the caller which role-specific dashboard endpoint they
    should be routed to. Any authenticated user can call this —
    the role-specific endpoints below are what actually enforce
    access.
    """

    return SuccessResponse[dict](
        message="Dashboard route resolved.",
        data={
            "role": current_user.role,
            "dashboard_path": f"/dashboard/{current_user.role}",
        },
    )


@router.get(
    "/citizen",
    response_model=SuccessResponse[dict],
    summary="Citizen dashboard (placeholder)",
)
async def citizen_dashboard(
    current_user: User = Depends(require_roles(ROLE_CITIZEN)),
) -> SuccessResponse[dict]:
    """
    Placeholder. Will show the citizen's own complaints, their
    statuses, and notifications once the Complaint module exists.
    """

    return SuccessResponse[dict](
        message="Citizen dashboard.",
        data={
            "name": current_user.name,
            "note": "Placeholder — real complaint/notification "
            "data lands here once the Complaint module is built.",
        },
    )


@router.get(
    "/officer",
    response_model=SuccessResponse[dict],
    summary="Officer dashboard (placeholder)",
)
async def officer_dashboard(
    current_user: User = Depends(require_roles(ROLE_OFFICER)),
) -> SuccessResponse[dict]:
    """
    Placeholder. Will show complaints assigned to this officer
    and ward-level complaint views once the Complaint/Officer
    APIs exist.
    """

    return SuccessResponse[dict](
        message="Officer dashboard.",
        data={
            "name": current_user.name,
            "note": "Placeholder — assigned complaints and "
            "ward views land here once the Officer module is built.",
        },
    )


@router.get(
    "/admin",
    response_model=SuccessResponse[dict],
    summary="Admin dashboard (placeholder)",
)
async def admin_dashboard(
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
) -> SuccessResponse[dict]:
    """
    Placeholder. Will show platform-wide analytics, user
    management, and department management once the Admin
    module exists.
    """

    return SuccessResponse[dict](
        message="Admin dashboard.",
        data={
            "name": current_user.name,
            "note": "Placeholder — analytics and user management "
            "land here once the Admin module is built.",
        },
    )