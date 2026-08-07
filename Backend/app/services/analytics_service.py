"""
Backs GET /analytics/summary (#142). Replaces the sample data the 3
analytics pages (citizen/staff/admin) render today with real numbers.

Scope is genuinely different per role, not just a visibility filter
like GET /complaints uses:
- citizen: complaints they filed
- staff: complaints assigned to them (their personal performance view,
  not every complaint in the system, that's what the admin dashboard
  is already for)
- admin: every complaint

Aggregation happens in Python rather than SQL GROUP BY, complaint
volumes here are small (matches rescore_all_complaints's same choice
in priority_service.py), and it keeps status/category counts and the
filing trend built from one query instead of three.
"""

from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select

from app.model import Complaint
from app.utils.constants import ROLE_ADMIN, ROLE_STAFF

FILING_TREND_DAYS = 14


async def get_analytics_summary(current_user, db) -> dict:
    query = select(Complaint)
    if current_user.role == ROLE_ADMIN:
        pass
    elif current_user.role == ROLE_STAFF:
        query = query.where(Complaint.assigned_to == current_user.id)
    else:
        query = query.where(Complaint.citizen_id == current_user.id)

    result = await db.execute(query)
    complaints = result.scalars().all()

    status_counts = Counter(c.status for c in complaints)
    category_counts = Counter(c.category for c in complaints)

    # created_at is stored as a naive datetime that's really UTC (see
    # complaint_service.py's own datetime.utcnow() usage), so "today"
    # has to be computed the same way, date.today() uses the server's
    # local timezone and would put complaints in the wrong day's
    # bucket whenever local time and UTC disagree on the calendar date.
    today = datetime.utcnow().date()
    trend_days = [today - timedelta(days=offset) for offset in range(FILING_TREND_DAYS - 1, -1, -1)]
    filed_by_day = Counter(c.created_at.date() for c in complaints)

    return {
        "total": len(complaints),
        "status_counts": dict(status_counts),
        "category_counts": dict(category_counts),
        "filing_trend": [
            {"date": day, "count": filed_by_day.get(day, 0)} for day in trend_days
        ],
    }
