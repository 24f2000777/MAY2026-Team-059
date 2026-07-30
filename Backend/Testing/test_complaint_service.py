"""
Pytest suite for complaint submission (#41).

Hits real Groq/LLM calls (via score_complaint's severity extraction and
route_complaint's department prediction) and real Supabase, same
reasoning as the other unmocked service suites in this project: this is
genuinely what needs proving, a mocked LLM response wouldn't catch a
real integration break between create_complaint and the ML services it
calls.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.model import ComplaintUpdate, Department, Notification, User
from app.schemas.complaint import ComplaintCreate, ComplaintLocation
from app.services.complaint_service import create_complaint, transition_complaint_status
from app.services.risk_alert_service import HIGH_RISK_NOTIFICATION_TYPE
from app.utils.constants import ROLE_ADMIN, ROLE_STAFF
from app.utils.exceptions import (
    ComplaintNotAssignedToUserError,
    ComplaintNotFoundError,
    InvalidStatusTransitionError,
)


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def citizen(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Citizen",
        email=f"pytest-{uuid.uuid4()}@example.com",
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
async def admin(db):
    # flag_if_high_risk only creates a notification if an admin exists to
    # receive one, without this, test_flags_high_risk_when_score_crosses_
    # threshold below would pass the threshold check but still find zero
    # notifications, same reasoning as test_risk_alert_service.py's fixture.
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
async def staff(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Staff",
        email=f"pytest-staff-{uuid.uuid4()}@example.com",
        role=ROLE_STAFF,
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


async def _make_complaint(db, citizen):
    data = ComplaintCreate(
        title="Large pothole on main road",
        description="There is a dangerous pothole near the school gate causing accidents daily.",
        category="pothole",
        location=ComplaintLocation(address="Near Patel Chowk, Patan"),
    )
    return await create_complaint(citizen.id, data, db)


class TestCreateComplaint:
    async def test_creates_complaint_with_address_location(self, db, citizen):
        data = ComplaintCreate(
            title="Large pothole on main road",
            description="There is a dangerous pothole near the school gate causing accidents daily.",
            category="pothole",
            location=ComplaintLocation(address="Near Patel Chowk, Patan"),
        )

        complaint = await create_complaint(citizen.id, data, db)

        assert complaint.id is not None
        assert complaint.citizen_id == citizen.id
        assert complaint.title == data.title
        assert complaint.description == data.description
        assert complaint.category == "pothole"
        assert complaint.location_text == "Near Patel Chowk, Patan"
        assert complaint.status == "submitted"
        assert isinstance(complaint.priority_score, int)
        assert 0 <= complaint.priority_score <= 100

        await _cleanup(db, complaint)

    async def test_creates_complaint_with_coordinates_only(self, db, citizen):
        data = ComplaintCreate(
            title="Streetlight out on Linking Road",
            description="The streetlight outside my building has been out for several days now.",
            category="streetlight",
            location=ComplaintLocation(latitude=19.0596, longitude=72.8295),
        )

        complaint = await create_complaint(citizen.id, data, db)

        assert complaint.location_text == "19.0596, 72.8295"

        await _cleanup(db, complaint)

    async def test_routes_to_a_department(self, db, citizen):
        data = ComplaintCreate(
            title="Water leak flooding the street",
            description="A burst water pipe is flooding the intersection near the market.",
            category="water_supply",
            location=ComplaintLocation(address="Near the market, Dadar"),
        )

        complaint = await create_complaint(citizen.id, data, db)

        # department_id can legitimately be None if departments haven't been
        # seeded in this environment (seed_departments runs on app startup,
        # not before a bare pytest run), but if it IS set, a water-related
        # complaint should route to the water supply department specifically.
        if complaint.department_id is not None:
            department = await db.get(Department, complaint.department_id)
            assert department.name == "Water Supply Department"

        await _cleanup(db, complaint)

    async def test_flags_high_risk_when_score_crosses_threshold(self, db, citizen, admin):
        # Can't force a specific score deterministically (real LLM severity
        # extraction), but if this complaint happens to score high, a
        # notification should exist, this is a real integration check, not
        # an assertion on the score's exact value.
        data = ComplaintCreate(
            title="Major gas leak near residential building",
            description="Strong smell of gas near the building entrance, multiple residents reporting dizziness, extremely urgent safety hazard.",
            category="other",
            location=ComplaintLocation(address="Residential Complex, Andheri"),
        )

        complaint = await create_complaint(citizen.id, data, db)

        result = await db.execute(
            select(Notification).where(
                Notification.complaint_id == complaint.id,
                Notification.type == HIGH_RISK_NOTIFICATION_TYPE,
            )
        )
        notifications = result.scalars().all()
        if complaint.priority_score >= 75:
            assert len(notifications) >= 1
        else:
            assert len(notifications) == 0

        await _cleanup(db, complaint)


class TestComplaintStatusStateMachine:
    async def test_full_happy_path_submitted_to_resolved(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        assert complaint.status == "submitted"

        approved = await transition_complaint_status(complaint.id, "approve", admin, None, db)
        assert approved.status == "approved"

        # assignment itself lives in a separate branch/PR, set it directly
        # here rather than depend on that endpoint existing yet
        complaint.assigned_to = staff.id
        await db.flush()

        started = await transition_complaint_status(complaint.id, "start", staff, "Heading out now.", db)
        assert started.status == "in_progress"

        resolved = await transition_complaint_status(complaint.id, "resolve", staff, "Pothole filled in.", db)
        assert resolved.status == "resolved"

        result = await db.execute(
            select(ComplaintUpdate)
            .where(ComplaintUpdate.complaint_id == complaint.id)
            .order_by(ComplaintUpdate.created_at)
        )
        updates = result.scalars().all()
        assert [u.new_status for u in updates] == ["approved", "in_progress", "resolved"]
        assert updates[0].old_status == "submitted"

        await _cleanup(db, complaint)

    async def test_reject_from_submitted_sets_reason(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)

        rejected = await transition_complaint_status(
            complaint.id, "reject", admin, "Duplicate of an existing complaint.", db
        )

        assert rejected.status == "rejected"
        assert rejected.reject_reason == "Duplicate of an existing complaint."

        await _cleanup(db, complaint)

    async def test_reject_from_approved_also_allowed(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)

        rejected = await transition_complaint_status(complaint.id, "reject", admin, "Changed our mind.", db)

        assert rejected.status == "rejected"

        await _cleanup(db, complaint)

    async def test_cannot_approve_a_non_submitted_complaint(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)

        with pytest.raises(InvalidStatusTransitionError):
            await transition_complaint_status(complaint.id, "approve", admin, None, db)

        await _cleanup(db, complaint)

    async def test_cannot_start_an_unassigned_complaint(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)

        with pytest.raises(InvalidStatusTransitionError):
            await transition_complaint_status(complaint.id, "start", staff, None, db)

        await _cleanup(db, complaint)

    async def test_cannot_start_a_complaint_still_submitted(self, db, citizen, staff):
        complaint = await _make_complaint(db, citizen)
        complaint.assigned_to = staff.id
        await db.flush()

        with pytest.raises(InvalidStatusTransitionError):
            await transition_complaint_status(complaint.id, "start", staff, None, db)

        await _cleanup(db, complaint)

    async def test_staff_cannot_start_someone_elses_assigned_complaint(self, db, citizen, admin, staff):
        other_staff = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Staff Two",
            email=f"pytest-staff-{uuid.uuid4()}@example.com",
            role=ROLE_STAFF,
            hashed_password="x",
            is_active=True,
        )
        db.add(other_staff)
        await db.flush()

        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        complaint.assigned_to = other_staff.id
        await db.flush()

        with pytest.raises(ComplaintNotAssignedToUserError):
            await transition_complaint_status(complaint.id, "start", staff, None, db)

        await _cleanup(db, complaint)
        await db.delete(other_staff)
        await db.commit()

    async def test_admin_can_start_any_complaint_regardless_of_assignee(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        complaint.assigned_to = staff.id
        await db.flush()

        # admin, not the assigned staff member, calling /start anyway
        started = await transition_complaint_status(complaint.id, "start", admin, None, db)
        assert started.status == "in_progress"

        await _cleanup(db, complaint)

    async def test_cannot_resolve_a_complaint_not_in_progress(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        complaint.assigned_to = staff.id
        await db.flush()

        with pytest.raises(InvalidStatusTransitionError):
            await transition_complaint_status(complaint.id, "resolve", staff, None, db)

        await _cleanup(db, complaint)

    async def test_transition_on_nonexistent_complaint_raises(self, db, admin):
        with pytest.raises(ComplaintNotFoundError):
            await transition_complaint_status(uuid.uuid4(), "approve", admin, None, db)
