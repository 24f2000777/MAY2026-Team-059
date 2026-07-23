"""
Routes a complaint to a department based on its category and description
(#69), by asking the LLM to pick one from the fixed department list
(app/chatbot/extractor.predict_department), same LLM-extraction approach
already used for severity in priority_service.py, rather than a trained
classifier.

Departments are looked up by their existing `name` column, no schema
change needed, department rows are seeded once (seed_departments, called
on app startup) rather than adding a mapping column to the departments
table.
"""

import logging

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.chatbot.extractor import predict_department
from app.model import Department
from app.utils.constants import DEPARTMENT_NAMES

logger = logging.getLogger(__name__)

DEPARTMENT_DESCRIPTIONS = {
    "Roads Department": "Potholes, road damage, and traffic-related complaints.",
    "Water Supply Department": "Water supply disruption and pipeline issues.",
    "Drainage & Sewerage Department": "Drainage overflow, flooding, and sewage issues.",
    "Solid Waste Management Department": "Garbage collection and solid waste.",
    "Street Lighting & Electrical Department": "Streetlight failures and electrical faults.",
    "General Administration Department": "Complaints that don't fit any other department.",
}

DEPARTMENT_SEEDS = [(name, DEPARTMENT_DESCRIPTIONS[name]) for name in DEPARTMENT_NAMES]


async def seed_departments(db) -> int:
    """
    Idempotent: inserts any of the fixed departments that don't already
    exist (by name), leaves existing rows untouched. Safe to call on
    every app startup.
    """
    result = await db.execute(select(Department.name))
    existing_names = {row[0] for row in result.all()}

    created = 0
    for name, description in DEPARTMENT_SEEDS:
        if name not in existing_names:
            db.add(Department(name=name, description=description))
            created += 1

    if created:
        await db.commit()

    return created


async def route_complaint(complaint, db) -> Department | None:
    """
    Asks the LLM which department the complaint belongs in, then looks up
    and returns that Department row. Does not persist department_id,
    callers decide that. Falls back to General Administration Department
    if the LLM call fails entirely, the same safe-default the routing
    prompt itself is told to use.
    """
    try:
        # predict_department is a blocking network call (LLM API), run it
        # in a thread so it doesn't stall the event loop for other requests
        department_name = await run_in_threadpool(
            predict_department, complaint.category, complaint.description
        )
    except Exception:
        logger.warning(
            "department routing failed for complaint %s, defaulting to General Administration",
            complaint.id,
            exc_info=True,
        )
        department_name = "General Administration Department"

    result = await db.execute(select(Department).where(Department.name == department_name))
    return result.scalar_one_or_none()
