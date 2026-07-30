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
    ComplaintResponse,
    StaffSummary,
)
from ..services.complaint_service import assign_complaint, create_complaint
from ..utils.constants import ROLE_ADMIN


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
