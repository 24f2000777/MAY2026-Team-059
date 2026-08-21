import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.services.priority_service import rescore_all_complaints

logger = logging.getLogger(__name__)


async def _rescore_all() -> int:
    async with AsyncSessionLocal() as db:
        return await rescore_all_complaints(db)


@celery_app.task(name="rescore_all_complaints_task")
def rescore_all_complaints_task() -> int:
    """
    Nightly job (2 AM IST, see celery_app.py's beat_schedule): recomputes
    priority_score for every complaint, same logic as POST /ml/rescore-all,
    just on a schedule instead of an HTTP call, since Celery Beat can't hit
    the API directly. Celery tasks in this codebase are plain sync
    functions, so the async DB/scoring logic runs via asyncio.run here.
    """
    rescored = asyncio.run(_rescore_all())
    logger.info("nightly priority rescore complete, %s complaints rescored", rescored)
    return rescored
