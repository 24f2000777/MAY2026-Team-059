import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.auth import get_current_user
from ..dependencies.roles import require_roles
from ..model import Complaint, User
from ..schemas.common import SuccessResponse
from ..services.priority_service import score_complaint
from ..utils.constants import ROLE_ADMIN, ROLE_STAFF

router = APIRouter(
    prefix="/ml",
    tags=["ML"],
)


async def _get_complaint_or_404(complaint_id: uuid.UUID, db: AsyncSession) -> Complaint:
    complaint = await db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found.")
    return complaint


@router.get("/priority/{complaint_id}")
async def get_priority(
    complaint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the complaint's current stored priority_score, without recomputing it."""
    complaint = await _get_complaint_or_404(complaint_id, db)
    return SuccessResponse[dict](
        message="Priority score retrieved.",
        data={"complaint_id": str(complaint.id), "priority_score": complaint.priority_score},
    )


@router.post("/priority/{complaint_id}")
async def rescore_complaint(
    complaint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_STAFF, ROLE_ADMIN)),
):
    """Recomputes and saves priority_score for a single complaint."""
    complaint = await _get_complaint_or_404(complaint_id, db)
    complaint.priority_score = round(await score_complaint(complaint, db))
    await db.commit()
    return SuccessResponse[dict](
        message="Priority score recomputed.",
        data={"complaint_id": str(complaint.id), "priority_score": complaint.priority_score},
    )


@router.post("/rescore-all")
async def rescore_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """Recomputes priority_score for every complaint. Meant for the nightly batch job."""
    result = await db.execute(select(Complaint))
    complaints = result.scalars().all()

    rescored = 0
    for complaint in complaints:
        complaint.priority_score = round(await score_complaint(complaint, db))
        rescored += 1

    await db.commit()
    return SuccessResponse[dict](
        message="Rescored all complaints.",
        data={"count": rescored},
    )
