from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.auth import get_current_user
from ..model import User
from ..schemas.analytics import AnalyticsSummaryResponse
from ..schemas.common import SuccessResponse
from ..services.analytics_service import get_analytics_summary

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get(
    "/summary",
    response_model=SuccessResponse[AnalyticsSummaryResponse],
    summary="Complaint volume and status breakdown, scoped to the caller's role",
)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Real numbers behind the analytics pages, no role check beyond
    being logged in, every role gets a real summary, just scoped to
    different complaints (see get_analytics_summary): citizens see
    their own filings, staff see what's assigned to them, admins see
    everything.
    """
    data = await get_analytics_summary(current_user, db)
    return SuccessResponse[AnalyticsSummaryResponse](
        message="Analytics summary retrieved.",
        data=AnalyticsSummaryResponse(**data),
    )
