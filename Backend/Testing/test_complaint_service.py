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
from app.schemas.complaint import (
    ComplaintAssignRequest,
    ComplaintCreate,
    ComplaintLocation,
    ComplaintStatus,
)
from app.services.complaint_service import assign_complaint, create_complaint
from app.services.risk_alert_service import HIGH_RISK_NOTIFICATION_TYPE
from app.utils.constants import ROLE_ADMIN, ROLE_STAFF
from app.utils.exceptions import (
    ComplaintNotAssignableError,
    ComplaintNotFoundError,
    InvalidStaffAssignmentError,
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


class TestAssignComplaint:
    async def test_assigns_without_changing_status(self, db, citizen, admin, staff):
        # Assigning is a "who" concern, not a "what stage" concern —
        # it deliberately leaves status untouched. See PATCH .../start
        # (the actual state machine) for the submitted/approved ->
        # in_progress transition.
        complaint = await _make_complaint(db, citizen)
        assert complaint.status == "submitted"

        request = ComplaintAssignRequest(assigned_to=staff.id, notes="Handle urgently")
        updated, returned_staff = await assign_complaint(complaint.id, admin.id, request, db)

        assert updated.id == complaint.id
        assert updated.assigned_to == staff.id
        assert updated.status == "submitted", "assigning must not change complaint status"
        assert returned_staff.id == staff.id

        result = await db.execute(
            select(ComplaintUpdate).where(ComplaintUpdate.complaint_id == complaint.id)
        )
        updates = result.scalars().all()
        assert len(updates) == 1
        assert updates[0].updated_by == admin.id
        assert updates[0].old_status is None
        assert updates[0].new_status is None
        assert updates[0].notes == "Handle urgently"

        await _cleanup(db, complaint)

    async def test_can_be_reassigned_to_a_different_staff_member(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)

        first_request = ComplaintAssignRequest(assigned_to=staff.id)
        await assign_complaint(complaint.id, admin.id, first_request, db)

        second_staff = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Staff Two",
            email=f"pytest-staff-{uuid.uuid4()}@example.com",
            role=ROLE_STAFF,
            hashed_password="x",
            is_active=True,
        )
        db.add(second_staff)
        await db.flush()

        second_request = ComplaintAssignRequest(assigned_to=second_staff.id)
        updated, returned_staff = await assign_complaint(complaint.id, admin.id, second_request, db)

        assert updated.assigned_to == second_staff.id
        assert returned_staff.id == second_staff.id

        # complaint.assigned_to still points at second_staff, delete it
        # first or the FK constraint rejects deleting the staff row
        await _cleanup(db, complaint)
        await db.delete(second_staff)
        await db.commit()

    async def test_rejects_assigning_to_a_citizen(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)

        request = ComplaintAssignRequest(assigned_to=citizen.id)
        with pytest.raises(InvalidStaffAssignmentError):
            await assign_complaint(complaint.id, admin.id, request, db)

        await _cleanup(db, complaint)

    async def test_rejects_assigning_to_a_nonexistent_user(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)

        request = ComplaintAssignRequest(assigned_to=uuid.uuid4())
        with pytest.raises(InvalidStaffAssignmentError):
            await assign_complaint(complaint.id, admin.id, request, db)

        await _cleanup(db, complaint)

    async def test_rejects_assigning_a_nonexistent_complaint(self, db, admin, staff):
        request = ComplaintAssignRequest(assigned_to=staff.id)
        with pytest.raises(ComplaintNotFoundError):
            await assign_complaint(uuid.uuid4(), admin.id, request, db)

    async def test_rejects_assigning_a_resolved_complaint(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        complaint.status = ComplaintStatus.RESOLVED.value
        await db.flush()

        request = ComplaintAssignRequest(assigned_to=staff.id)
        with pytest.raises(ComplaintNotAssignableError):
            await assign_complaint(complaint.id, admin.id, request, db)

        await _cleanup(db, complaint)

    async def test_rejects_assigning_a_withdrawn_complaint(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        complaint.status = ComplaintStatus.WITHDRAWN.value
        await db.flush()

        request = ComplaintAssignRequest(assigned_to=staff.id)
        with pytest.raises(ComplaintNotAssignableError):
            await assign_complaint(complaint.id, admin.id, request, db)

        await _cleanup(db, complaint)
