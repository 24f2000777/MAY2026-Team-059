from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.auth import get_current_user
from ..dependencies.roles import require_roles
from ..model import Department, User
from ..schemas.common import SuccessResponse
from ..schemas.complaint import (
    ComplaintAssignRequest,
    ComplaintAssignResponse,
    ComplaintCreate,
    ComplaintNote,
    ComplaintNoteAuthor,
    ComplaintNoteCreateRequest,
    ComplaintNoteListResponse,
    ComplaintRejectRequest,
    ComplaintResponse,
    ComplaintStatusResponse,
    ComplaintTransitionRequest,
    MyComplaintListResponse,
    MyComplaintOut,
    StaffSummary,
    WardListResponse,
    WardOut,
)
from ..services.complaint_service import (
    add_complaint_note,
    assign_complaint,
    create_complaint,
    list_complaint_notes,
    list_my_complaints,
    transition_complaint_status,
)
from ..utils.constants import ROLE_ADMIN, ROLE_STAFF
from ..utils.wards import WARDS


router = APIRouter(
    prefix="/complaints",
    tags=["Complaints"],
)

@router.get("/whoami")
async def whoami(current_user: User = Depends(get_current_user)):
    return {"id": str(current_user.id), "email": current_user.email}


@router.get(
    "/wards",
    response_model=SuccessResponse[WardListResponse],
    summary="List the 24 real BMC administrative wards",
)
async def list_wards(current_user: User = Depends(get_current_user)):
    """
    Static reference data (Mumbai's wards don't change at runtime), used
    to populate a ward picker on complaint submission. Selecting a real
    ward improves priority scoring accuracy (see priority_service.py).
    """
    wards = [
        WardOut(code=w.code, area=w.area, zone=w.zone, ward_type=w.ward_type, population_density=w.population_density)
        for w in sorted(WARDS.values(), key=lambda w: w.code)
    ]
    return SuccessResponse[WardListResponse](
        message="Wards retrieved.",
        data=WardListResponse(wards=wards),
    )


@router.get(
    "/mine",
    response_model=SuccessResponse[MyComplaintListResponse],
    summary="List the current citizen's own complaints",
)
async def list_my_complaints_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Every complaint the calling citizen has filed, newest first, whether
    it came from POST /complaints or the chatbot. Backs the "My
    Complaints" dashboard.
    """
    complaints = await list_my_complaints(current_user.id, db)
    return SuccessResponse[MyComplaintListResponse](
        message="Complaints retrieved.",
        data=MyComplaintListResponse(
            complaints=[MyComplaintOut.model_validate(c) for c in complaints]
        ),
    )


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


@router.patch(
    "/{complaint_id}/assign",
    response_model=SuccessResponse[ComplaintAssignResponse],
    summary="Assign a complaint to a staff member (admin only)",
)
async def assign_complaint_route(
    complaint_id: UUID,
    body: ComplaintAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Assigns a complaint to a staff member. Only admins can call this.
    Does not change the complaint's status, "who's responsible" and
    "what stage it's at" are separate — see PATCH .../start for the
    actual submitted/approved -> in_progress transition, which
    requires the complaint to already be assigned first.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        ComplaintNotAssignableError: 409, if the complaint is already
            resolved, closed, rejected, or withdrawn.
        InvalidStaffAssignmentError: 422, if assigned_to isn't an
            existing user with role 'staff'.
    """
    complaint, staff = await assign_complaint(complaint_id, current_user.id, body, db)
    await db.commit()

    # updated_at is server-computed (onupdate=func.now()), so SQLAlchemy
    # marks it expired after the UPDATE regardless of expire_on_commit,
    # an implicit lazy-reload of it outside an active await context
    # raises MissingGreenlet. ComplaintAssignResponse includes
    # updated_at (ComplaintResponse from POST /complaints doesn't,
    # which is why this didn't surface there), so refresh explicitly
    # instead of touching an expired attribute.
    await db.refresh(complaint)

    department_name = None
    if staff.department_id:
        department = await db.get(Department, staff.department_id)
        department_name = department.name if department else None

    return SuccessResponse[ComplaintAssignResponse](
        message="Complaint assigned.",
        data=ComplaintAssignResponse(
            id=complaint.id,
            title=complaint.title,
            description=complaint.description,
            category=complaint.category,
            status=complaint.status,
            priority_score=complaint.priority_score,
            assigned_to=complaint.assigned_to,
            staff_details=StaffSummary(
                id=staff.id,
                name=staff.name,
                role=staff.role,
                department=department_name,
            ),
            citizen_id=complaint.citizen_id,
            created_at=complaint.created_at,
            updated_at=complaint.updated_at,
        ),
    )


def _to_complaint_note(update, author) -> ComplaintNote:
    return ComplaintNote(
        id=update.id,
        complaint_id=update.complaint_id,
        note_text=update.notes,
        author=ComplaintNoteAuthor(id=author.id, name=author.name, role=author.role),
        created_at=update.created_at,
    )


@router.post(
    "/{complaint_id}/updates",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[ComplaintNote],
    summary="Add an internal note to a complaint (staff/admin only)",
)
async def add_complaint_note_route(
    complaint_id: UUID,
    body: ComplaintNoteCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_STAFF, ROLE_ADMIN)),
):
    """
    Adds an internal note to a complaint. Staff or admin only, never
    visible to the citizen who filed the complaint.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
    """
    note, author = await add_complaint_note(complaint_id, current_user.id, body.note_text, db)
    await db.commit()

    return SuccessResponse[ComplaintNote](
        message="Note added.",
        data=_to_complaint_note(note, author),
    )


@router.get(
    "/{complaint_id}/updates",
    response_model=SuccessResponse[ComplaintNoteListResponse],
    summary="List internal notes on a complaint (staff/admin only)",
)
async def list_complaint_notes_route(
    complaint_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_STAFF, ROLE_ADMIN)),
):
    """
    Lists every internal note on a complaint, oldest first. Staff or
    admin only, never visible to the citizen who filed the complaint.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
    """
    notes = await list_complaint_notes(complaint_id, db)

    return SuccessResponse[ComplaintNoteListResponse](
        message="Notes retrieved.",
        data=ComplaintNoteListResponse(
            notes=[_to_complaint_note(note, author) for note, author in notes]
        ),
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
