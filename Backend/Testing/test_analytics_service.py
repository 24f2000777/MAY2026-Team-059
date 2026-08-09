"""
Pytest suite for GET /analytics/summary (#142).

Hits real Supabase, same reasoning as the other unmocked service
suites in this project. Citizen/staff scope tests use exact counts,
safe since each test's fixtures are freshly created, randomized users
with no other complaints attached to them. The admin scope test can't
do that (admin sees every complaint in the shared table, other tests
and real data included), so it asserts on the delta a known new
complaint causes instead of an absolute total.
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.model import Notification, User
from app.schemas.complaint import ComplaintCreate, ComplaintLocation
from app.services.analytics_service import get_analytics_summary
from app.services.complaint_service import create_complaint


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def citizen(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Analytics Citizen",
        email=f"pytest-analytics-{uuid.uuid4()}@example.com",
        role="citizen",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    yield user
    await db.delete(user)
    await db.commit()


@pytest.fixture
async def other_citizen(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Analytics Other Citizen",
        email=f"pytest-analytics-other-{uuid.uuid4()}@example.com",
        role="citizen",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    yield user
    await db.delete(user)
    await db.commit()


@pytest.fixture
async def staff(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Analytics Staff",
        email=f"pytest-analytics-staff-{uuid.uuid4()}@example.com",
        role="staff",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    yield user
    await db.delete(user)
    await db.commit()


@pytest.fixture
async def admin(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Analytics Admin",
        email=f"pytest-analytics-admin-{uuid.uuid4()}@example.com",
        role="admin",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    yield user
    await db.delete(user)
    await db.commit()


async def _cleanup(db, complaint):
    result = await db.execute(select(Notification).where(Notification.complaint_id == complaint.id))
    for n in result.scalars().all():
        await db.delete(n)
    await db.delete(complaint)
    await db.commit()


async def _make_complaint(db, citizen, category="pothole"):
    data = ComplaintCreate(
        title="Large pothole on main road",
        description="There is a dangerous pothole near the school gate causing accidents daily.",
        category=category,
        location=ComplaintLocation(address="Near Patel Chowk, Patan"),
    )
    return await create_complaint(citizen.id, data, db)


class TestGetAnalyticsSummary:
    async def test_citizen_only_sees_their_own_complaints(self, db, citizen, other_citizen):
        mine = await _make_complaint(db, citizen, category="pothole")
        theirs = await _make_complaint(db, other_citizen, category="garbage")
        await db.commit()

        summary = await get_analytics_summary(citizen, db)

        assert summary["total"] == 1
        assert summary["category_counts"] == {"pothole": 1}
        assert summary["status_counts"] == {"submitted": 1}

        await _cleanup(db, mine)
        await _cleanup(db, theirs)

    async def test_staff_only_sees_complaints_assigned_to_them(self, db, citizen, staff, admin):
        assigned = await _make_complaint(db, citizen, category="pothole")
        unassigned = await _make_complaint(db, citizen, category="garbage")
        assigned.assigned_to = staff.id
        await db.commit()

        summary = await get_analytics_summary(staff, db)

        assert summary["total"] == 1
        assert summary["category_counts"] == {"pothole": 1}

        await _cleanup(db, assigned)
        await _cleanup(db, unassigned)

    async def test_admin_sees_every_complaint_including_ones_not_their_own(self, db, citizen, admin):
        before = await get_analytics_summary(admin, db)

        complaint = await _make_complaint(db, citizen, category="pothole")
        await db.commit()

        after = await get_analytics_summary(admin, db)

        assert after["total"] == before["total"] + 1
        assert after["status_counts"]["submitted"] == before["status_counts"].get("submitted", 0) + 1
        assert after["category_counts"]["pothole"] == before["category_counts"].get("pothole", 0) + 1

        await _cleanup(db, complaint)

    async def test_filing_trend_covers_the_last_14_days_zero_filled(self, db, citizen):
        complaint = await _make_complaint(db, citizen)
        await db.commit()

        summary = await get_analytics_summary(citizen, db)

        assert len(summary["filing_trend"]) == 14
        # created_at is naive UTC, the trend bucketing has to match, not
        # the test machine's local calendar date (see the same
        # date.today()-vs-UTC bug just fixed in analytics_service.py).
        assert summary["filing_trend"][-1]["date"] == datetime.utcnow().date()
        assert summary["filing_trend"][-1]["count"] == 1
        # A citizen fixture is created fresh in this test alone, so every
        # earlier day in the window has nothing filed against it yet.
        assert all(point["count"] == 0 for point in summary["filing_trend"][:-1])

        await _cleanup(db, complaint)

    async def test_returns_zero_state_for_a_citizen_with_no_complaints(self, db, citizen):
        summary = await get_analytics_summary(citizen, db)

        assert summary["total"] == 0
        assert summary["status_counts"] == {}
        assert summary["category_counts"] == {}
        assert len(summary["filing_trend"]) == 14
        assert all(point["count"] == 0 for point in summary["filing_trend"])
