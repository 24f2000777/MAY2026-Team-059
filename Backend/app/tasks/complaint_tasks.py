import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.services.complaint_service import auto_close_stale_resolved_complaints

logger = logging.getLogger(__name__)


async def _auto_close_stale_resolved() -> int:
    async with AsyncSessionLocal() as db:
        return await auto_close_stale_resolved_complaints(db)


@celery_app.task(name="auto_close_stale_resolved_complaints_task")
def auto_close_stale_resolved_complaints_task() -> int:
    """
    Nightly job (2 AM IST, see celery_app.py's beat_schedule): closes
    every complaint that's been sitting in 'resolved' for 7+ days with
    no citizen confirmation, the "System" actor the design doc lists
    for the close transition. Celery tasks in this codebase are plain
    sync functions, so the async DB logic runs via asyncio.run here,
    same pattern as priority_tasks.py's nightly rescore.
    """
    closed = asyncio.run(_auto_close_stale_resolved())
    logger.info("auto-close job complete, %s complaints closed", closed)
    return closed
