from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.auth import get_current_user
from ..dependencies.roles import require_roles
from ..model import User
from ..schemas.common import SuccessResponse
from ..schemas.complaint import (
    ComplaintCreate,
    ComplaintRejectRequest,
    ComplaintResponse,
    ComplaintStatusResponse,
    ComplaintTransitionRequest,
)
from ..services.complaint_service import create_complaint, transition_complaint_status
from ..utils.constants import ROLE_ADMIN, ROLE_STAFF


router = APIRouter(
    prefix="/complaints",
    tags=["Complaints"],
)

@router.get("/whoami")
async def whoami(current_user: User = Depends(get_current_user)):
    return {"id": str(current_user.id), "email": current_user.email}


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_complaint(
    body: ComplaintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Files a new complaint and immediately scores/routes it (priority
    score, department, high-risk flag) using the same ML services the
    /ml/* endpoints expose individually.
    """
    complaint = await create_complaint(current_user.id, body, db)
    await db.commit()
    return SuccessResponse[ComplaintResponse](
        message="Complaint submitted.",
        data=ComplaintResponse.model_validate(complaint),
    )


async def _transition_and_respond(complaint_id, action, actor, notes, message, db):
    """
    Shared by all four transition routes below: run the transition,
    commit, refresh (status/reject_reason are set in Python so those
    are already fresh, but updated_at is server-computed via
    onupdate=func.now(), same MissingGreenlet risk PR #120 hit,
    refresh explicitly rather than touch an expired attribute), and
    wrap the result in the standard envelope.
    """
    complaint = await transition_complaint_status(complaint_id, action, actor, notes, db)
    await db.commit()
    await db.refresh(complaint)

    return SuccessResponse[ComplaintStatusResponse](
        message=message,
        data=ComplaintStatusResponse.model_validate(complaint),
    )


@router.patch(
    "/{complaint_id}/approve",
    response_model=SuccessResponse[ComplaintStatusResponse],
    summary="Approve a submitted complaint (admin only)",
)
async def approve_complaint_route(
    complaint_id: UUID,
    body: ComplaintTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    submitted -> approved. Only admins can call this.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        InvalidStatusTransitionError: 409, if the complaint isn't
            currently "submitted".
    """
    return await _transition_and_respond(
        complaint_id, "approve", current_user, body.notes, "Complaint approved.", db
    )


@router.patch(
    "/{complaint_id}/reject",
    response_model=SuccessResponse[ComplaintStatusResponse],
    summary="Reject a complaint (admin only)",
)
async def reject_complaint_route(
    complaint_id: UUID,
    body: ComplaintRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    submitted or approved -> rejected. Only admins can call this.
    Unlike approve/start/resolve, a reason is required, not optional,
    and is stored on Complaint.reject_reason as well as logged.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        InvalidStatusTransitionError: 409, if the complaint isn't
            currently "submitted" or "approved".
    """
    return await _transition_and_respond(
        complaint_id, "reject", current_user, body.reason, "Complaint rejected.", db
    )


@router.patch(
    "/{complaint_id}/start",
    response_model=SuccessResponse[ComplaintStatusResponse],
    summary="Start work on an approved, assigned complaint (staff/admin only)",
)
async def start_complaint_route(
    complaint_id: UUID,
    body: ComplaintTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_STAFF, ROLE_ADMIN)),
):
    """
    approved -> in_progress. Staff or admin. The complaint must
    already be assigned (see PATCH .../assign) — a staff caller can
    only start their own assigned work, an admin can start any.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        InvalidStatusTransitionError: 409, if the complaint isn't
            currently "approved", or isn't assigned to anyone yet.
        ComplaintNotAssignedToUserError: 403, if a staff caller isn't
            the complaint's assigned staff member.
    """
    return await _transition_and_respond(
        complaint_id, "start", current_user, body.notes, "Work started.", db
    )


@router.patch(
    "/{complaint_id}/resolve",
    response_model=SuccessResponse[ComplaintStatusResponse],
    summary="Mark an in-progress complaint resolved (staff/admin only)",
)
async def resolve_complaint_route(
    complaint_id: UUID,
    body: ComplaintTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_STAFF, ROLE_ADMIN)),
):
    """
    in_progress -> resolved. Staff or admin, same assignment rule as
    /start.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        InvalidStatusTransitionError: 409, if the complaint isn't
            currently "in_progress".
        ComplaintNotAssignedToUserError: 403, if a staff caller isn't
            the complaint's assigned staff member.
    """
    return await _transition_and_respond(
        complaint_id, "resolve", current_user, body.notes, "Complaint resolved.", db
    )
