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
from app.services.complaint_service import (
    add_complaint_note,
    assign_complaint,
    create_complaint,
    list_complaint_notes,
    transition_complaint_status,
)
from app.services.risk_alert_service import HIGH_RISK_NOTIFICATION_TYPE
from app.utils.constants import ROLE_ADMIN, ROLE_STAFF
from app.utils.exceptions import (
    ComplaintNotAssignableError,
    ComplaintNotAssignedToUserError,
    ComplaintNotFoundError,
    InvalidStaffAssignmentError,
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


class TestComplaintNotes:
    async def test_adds_a_note_without_changing_status(self, db, citizen, staff):
        complaint = await _make_complaint(db, citizen)

        note, author = await add_complaint_note(
            complaint.id, staff.id, "Spoke with resident, scheduling a follow-up.", db
        )

        assert note.complaint_id == complaint.id
        assert note.notes == "Spoke with resident, scheduling a follow-up."
        assert note.updated_by == staff.id
        assert note.old_status is None
        assert note.new_status is None
        assert author.id == staff.id
        assert complaint.status == "submitted", "adding a note must not touch complaint status"

        await _cleanup(db, complaint)

    async def test_admin_can_also_add_a_note(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)

        note, author = await add_complaint_note(complaint.id, admin.id, "Escalating this one.", db)

        assert note.updated_by == admin.id
        assert author.id == admin.id

        await _cleanup(db, complaint)

    async def test_lists_notes_oldest_first(self, db, citizen, staff, admin):
        complaint = await _make_complaint(db, citizen)

        await add_complaint_note(complaint.id, staff.id, "First note.", db)
        await add_complaint_note(complaint.id, admin.id, "Second note.", db)

        notes = await list_complaint_notes(complaint.id, db)

        assert len(notes) == 2
        assert notes[0][0].notes == "First note."
        assert notes[0][1].id == staff.id
        assert notes[1][0].notes == "Second note."
        assert notes[1][1].id == admin.id

        await _cleanup(db, complaint)

    async def test_pure_status_change_rows_are_not_listed_as_notes(self, db, citizen, staff, admin):
        # A ComplaintUpdate row with no note text (a bare status change,
        # not something this endpoint ever creates itself today, but the
        # table is shared, so this proves the filter actually excludes
        # rows without commentary rather than showing every row).
        complaint = await _make_complaint(db, citizen)
        db.add(ComplaintUpdate(
            complaint_id=complaint.id,
            updated_by=admin.id,
            old_status="submitted",
            new_status="approved",
            notes=None,
        ))
        await add_complaint_note(complaint.id, staff.id, "This one has real text.", db)

        notes = await list_complaint_notes(complaint.id, db)

        assert len(notes) == 1
        assert notes[0][0].notes == "This one has real text."

        await _cleanup(db, complaint)

    async def test_rejects_adding_a_note_to_a_nonexistent_complaint(self, db, staff):
        with pytest.raises(ComplaintNotFoundError):
            await add_complaint_note(uuid.uuid4(), staff.id, "Doesn't matter.", db)

    async def test_rejects_listing_notes_for_a_nonexistent_complaint(self, db):
        with pytest.raises(ComplaintNotFoundError):
            await list_complaint_notes(uuid.uuid4(), db)


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

    async def test_reject_clears_assignment(self, db, citizen, admin, staff):
        # A rejected complaint is terminal, it shouldn't keep showing up
        # as "assigned" to whichever staff member had it.
        complaint = await _make_complaint(db, citizen)
        complaint.assigned_to = staff.id
        await db.flush()

        rejected = await transition_complaint_status(complaint.id, "reject", admin, "No longer valid.", db)

        assert rejected.assigned_to is None

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
