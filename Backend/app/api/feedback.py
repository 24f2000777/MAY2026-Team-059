from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.roles import require_roles
from ..model import User
from ..schemas.common import SuccessResponse
from ..schemas.feedback import FeedbackOut, FeedbackSummaryResponse, OfficerRatingsResponse
from ..services.feedback_service import get_feedback_summary, get_officer_ratings
from ..utils.constants import ROLE_ADMIN
from ..utils.exceptions import UserNotFoundError

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"],
)


@router.get(
    "/officer/{officer_id}",
    response_model=SuccessResponse[OfficerRatingsResponse],
    summary="Get aggregated ratings for an officer (admin only)",
)
async def get_officer_ratings_route(
    officer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Raises:
        UserNotFoundError: 404, if officer_id isn't a real user.
    """
    officer, ratings, average = await get_officer_ratings(officer_id, db)
    if officer is None:
        raise UserNotFoundError("Officer not found.")

    return SuccessResponse[OfficerRatingsResponse](
        message="Officer ratings retrieved.",
        data=OfficerRatingsResponse(
            officer_id=officer.id,
            officer_name=officer.name,
            average_score=average,
            total_ratings=len(ratings),
            ratings=[FeedbackOut.model_validate(r) for r in ratings],
        ),
    )


@router.get(
    "/summary",
    response_model=SuccessResponse[FeedbackSummaryResponse],
    summary="Platform-wide feedback analytics (admin only)",
)
async def get_feedback_summary_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    total, average, distribution = await get_feedback_summary(db)

    return SuccessResponse[FeedbackSummaryResponse](
        message="Feedback summary retrieved.",
        data=FeedbackSummaryResponse(
            average_score=average,
            total_ratings=total,
            score_distribution=distribution,
        ),
    )
