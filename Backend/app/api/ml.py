import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.auth import get_current_user
from ..dependencies.roles import require_roles
from ..model import Complaint, Department, User
from ..schemas.common import SuccessResponse
from ..services.category_service import predict_category
from ..services.priority_service import rescore_all_complaints, score_complaint
from ..services.risk_alert_service import HIGH_RISK_THRESHOLD, flag_if_high_risk
from ..services.routing_service import route_complaint
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
    """Recomputes and saves priority_score for a single complaint, flagging it if high-risk."""
    complaint = await _get_complaint_or_404(complaint_id, db)
    complaint.priority_score = round(await score_complaint(complaint, db))
    await db.commit()
    flagged = await flag_if_high_risk(complaint, db)
    return SuccessResponse[dict](
        message="Priority score recomputed.",
        data={
            "complaint_id": str(complaint.id),
            "priority_score": complaint.priority_score,
            "flagged_high_risk": flagged,
        },
    )


@router.post("/rescore-all")
async def rescore_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """Recomputes priority_score for every complaint. Also runs nightly via Celery Beat."""
    rescored = await rescore_all_complaints(db)
    return SuccessResponse[dict](
        message="Rescored all complaints.",
        data={"count": rescored},
    )


@router.get("/categorize/{complaint_id}")
async def get_category(
    complaint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the complaint's current category, without recomputing it."""
    complaint = await _get_complaint_or_404(complaint_id, db)
    return SuccessResponse[dict](
        message="Category retrieved.",
        data={"complaint_id": str(complaint.id), "category": complaint.category},
    )


@router.post("/categorize/{complaint_id}")
async def recategorize_complaint(
    complaint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_STAFF, ROLE_ADMIN)),
):
    """Re-predicts and overwrites category from the complaint's own title/description."""
    complaint = await _get_complaint_or_404(complaint_id, db)
    complaint.category = await predict_category(f"{complaint.title}. {complaint.description}")
    await db.commit()
    return SuccessResponse[dict](
        message="Category recomputed.",
        data={"complaint_id": str(complaint.id), "category": complaint.category},
    )


@router.get("/route-department/{complaint_id}")
async def get_department(
    complaint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the complaint's current department assignment, without recomputing it."""
    complaint = await _get_complaint_or_404(complaint_id, db)
    department = await db.get(Department, complaint.department_id) if complaint.department_id else None
    return SuccessResponse[dict](
        message="Department retrieved.",
        data={
            "complaint_id": str(complaint.id),
            "department_id": str(complaint.department_id) if complaint.department_id else None,
            "department_name": department.name if department else None,
        },
    )


@router.post("/route-department/{complaint_id}")
async def route_department(
    complaint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_STAFF, ROLE_ADMIN)),
):
    """Re-routes the complaint to a department based on its current category and description."""
    complaint = await _get_complaint_or_404(complaint_id, db)
    department = await route_complaint(complaint, db)
    complaint.department_id = department.id if department else None
    await db.commit()
    return SuccessResponse[dict](
        message="Department routed.",
        data={
            "complaint_id": str(complaint.id),
            "department_id": str(complaint.department_id) if complaint.department_id else None,
            "department_name": department.name if department else None,
        },
    )


@router.get("/high-risk")
async def list_high_risk_complaints(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_STAFF, ROLE_ADMIN)),
):
    """Lists every complaint currently at or above the high-risk priority threshold (#24)."""
    result = await db.execute(
        select(Complaint)
        .where(Complaint.priority_score >= HIGH_RISK_THRESHOLD)
        .order_by(Complaint.priority_score.desc())
    )
    complaints = result.scalars().all()
    return SuccessResponse[dict](
        message="High-risk complaints retrieved.",
        data={
            "threshold": HIGH_RISK_THRESHOLD,
            "count": len(complaints),
            "complaints": [
                {
                    "id": str(c.id),
                    "title": c.title,
                    "category": c.category,
                    "priority_score": c.priority_score,
                }
                for c in complaints
            ],
        },
    )
