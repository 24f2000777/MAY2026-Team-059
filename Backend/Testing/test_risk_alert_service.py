"""
Pytest suite for auto-flagging high-risk complaints (#24).

No mocking needed here, unlike the LLM-backed suites, flag_if_high_risk
only touches the database (no LLM call), so every test runs fast and
free against real Supabase.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.model import Complaint, Notification, User
from app.services.risk_alert_service import (
    HIGH_RISK_NOTIFICATION_TYPE,
    HIGH_RISK_THRESHOLD,
    flag_if_high_risk,
)
from app.utils.constants import ROLE_ADMIN


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def admin(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Admin",
        email=f"pytest-admin-{uuid.uuid4()}@example.com",
        role=ROLE_ADMIN,
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    yield user
    await db.delete(user)
    await db.commit()


@pytest.fixture
async def citizen(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Citizen",
        email=f"pytest-citizen-{uuid.uuid4()}@example.com",
        role="citizen",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    yield user
    await db.delete(user)
    await db.commit()


async def _make_complaint(db, citizen, priority_score):
    complaint = Complaint(
        citizen_id=citizen.id,
        title="Pytest test complaint",
        description="A test complaint for the risk alert suite.",
        category="road",
        location_text="Test Location",
        priority_score=priority_score,
    )
    db.add(complaint)
    await db.flush()
    return complaint


class TestFlagIfHighRisk:
    async def test_does_not_flag_below_threshold(self, db, admin, citizen):
        complaint = await _make_complaint(db, citizen, HIGH_RISK_THRESHOLD - 1)

        flagged = await flag_if_high_risk(complaint, db)
        assert flagged is False

        result = await db.execute(
            select(Notification).where(Notification.complaint_id == complaint.id)
        )
        assert result.first() is None

        await db.delete(complaint)
        await db.commit()

    async def test_flags_at_or_above_threshold_and_notifies_admins(self, db, admin, citizen):
        complaint = await _make_complaint(db, citizen, HIGH_RISK_THRESHOLD)

        flagged = await flag_if_high_risk(complaint, db)
        assert flagged is True

        result = await db.execute(
            select(Notification).where(
                Notification.complaint_id == complaint.id,
                Notification.type == HIGH_RISK_NOTIFICATION_TYPE,
            )
        )
        notifications = result.scalars().all()
        assert len(notifications) == 1
        assert notifications[0].user_id == admin.id
        assert str(complaint.priority_score) in notifications[0].message

        await db.delete(notifications[0])
        await db.delete(complaint)
        await db.commit()

    async def test_does_not_duplicate_notification_on_second_call(self, db, admin, citizen):
        complaint = await _make_complaint(db, citizen, 95)

        first_call = await flag_if_high_risk(complaint, db)
        second_call = await flag_if_high_risk(complaint, db)

        assert first_call is True
        assert second_call is False

        result = await db.execute(
            select(Notification).where(Notification.complaint_id == complaint.id)
        )
        assert len(result.scalars().all()) == 1

        for n in result.scalars().all():
            await db.delete(n)
        await db.delete(complaint)
        await db.commit()

    async def test_notifies_every_admin_not_just_one(self, db, citizen):
        admin1 = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}", name="Admin One",
            email=f"pytest-admin1-{uuid.uuid4()}@example.com",
            role=ROLE_ADMIN, hashed_password="x", is_active=True,
        )
        admin2 = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}", name="Admin Two",
            email=f"pytest-admin2-{uuid.uuid4()}@example.com",
            role=ROLE_ADMIN, hashed_password="x", is_active=True,
        )
        db.add_all([admin1, admin2])
        await db.flush()

        complaint = await _make_complaint(db, citizen, 99)
        await flag_if_high_risk(complaint, db)

        result = await db.execute(
            select(Notification).where(Notification.complaint_id == complaint.id)
        )
        notified_user_ids = {n.user_id for n in result.scalars().all()}
        assert {admin1.id, admin2.id} <= notified_user_ids

        for n in result.scalars().all():
            await db.delete(n)
        await db.delete(complaint)
        await db.delete(admin1)
        await db.delete(admin2)
        await db.commit()
