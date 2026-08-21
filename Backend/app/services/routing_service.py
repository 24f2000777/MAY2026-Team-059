"""
Routes a complaint to a department based on its category (#69), via the
fixed, deterministic CATEGORY_TO_DEPARTMENT lookup in app/utils/constants.py.

This used to ask an LLM to pick a department per-complaint (same
LLM-extraction approach still used for severity in priority_service.py).
Dropped in favor of a plain lookup: category is already one of a fixed,
controlled set by the time a complaint reaches this function, so there's
no genuine ambiguity to resolve, and the LLM call was a real source of
misrouting in practice (a real drainage complaint landed in General
Administration) for a decision that has exactly one correct answer per
category.

Departments are looked up by their existing `name` column, no schema
change needed, department rows are seeded once (seed_departments, called
on app startup) rather than adding a mapping column to the departments
table.
"""

import logging

from sqlalchemy import select

from app.model import Department
from app.utils.constants import CATEGORY_TO_DEPARTMENT, DEPARTMENT_NAMES

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
    Looks up complaint.category in CATEGORY_TO_DEPARTMENT and returns the
    matching Department row. Does not persist department_id, callers
    decide that. Falls back to General Administration Department if the
    category somehow isn't in the mapping (shouldn't happen, every
    ComplaintCategory value has an entry, see the mapping's own comment)
    or the departments table hasn't been seeded yet.
    """
    category = complaint.category.value if hasattr(complaint.category, "value") else complaint.category
    department_name = CATEGORY_TO_DEPARTMENT.get(category)

    if department_name is None:
        logger.warning(
            "no department mapping for category '%s' on complaint %s, defaulting to General Administration",
            category,
            complaint.id,
        )
        department_name = "General Administration Department"

    result = await db.execute(select(Department).where(Department.name == department_name))
    department = result.scalar_one_or_none()

    if department is None:
        # department_name came from our own fixed CATEGORY_TO_DEPARTMENT
        # mapping, so this branch means the departments table hasn't
        # been seeded yet (see seed_departments), not a bad mapping.
        logger.warning(
            "department '%s' not found in table (not seeded yet?), falling back to General Administration",
            department_name,
        )
        result = await db.execute(
            select(Department).where(Department.name == "General Administration Department")
        )
        department = result.scalar_one_or_none()

    return department
