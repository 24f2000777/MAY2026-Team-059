"""
Pytest suite for complaint submission (#41).

Hits real Groq/LLM calls (via score_complaint's severity extraction) and
real Supabase, same reasoning as the other unmocked service suites in
this project: this is genuinely what needs proving, a mocked LLM
response wouldn't catch a real integration break between create_complaint
and the ML services it calls. route_complaint's department routing is a
plain deterministic lookup, not an LLM call (see routing_service.py).
"""

import csv
import io
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.model import (
    ChatSession,
    Complaint,
    ComplaintImage,
    ComplaintUpdate,
    Department,
    Notification,
    User,
)
from app.schemas.complaint import (
    ComplaintAssignRequest,
    ComplaintCreate,
    ComplaintLocation,
    ComplaintStatus,
)
from app.core.config import settings
from app.services.complaint_service import (
    AUTO_CLOSE_AFTER_DAYS,
    add_complaint_note,
    assign_complaint,
    auto_close_stale_resolved_complaints,
    create_complaint,
    delete_attachment,
    delete_complaint,
    edit_complaint,
    export_complaints_csv,
    get_attachment,
    get_complaint_detail,
    get_complaint_history,
    list_complaint_attachments,
    list_complaint_notes,
    list_complaints,
    list_complaints_by_category,
    list_complaints_by_ward,
    list_my_complaints,
    transition_complaint_status,
    transition_complaint_status_as_owner,
    upload_complaint_attachment,
)
from app.services.risk_alert_service import HIGH_RISK_NOTIFICATION_TYPE
from app.utils.constants import ROLE_ADMIN, ROLE_STAFF
from app.utils.exceptions import (
    AttachmentNotFoundError,
    ComplaintNotAssignableError,
    ComplaintNotAssignedToUserError,
    ComplaintNotFoundError,
    ComplaintNotOwnerError,
    ComplaintNotResolvedError,
    FileTooLargeError,
    InsufficientPermissionsError,
    InvalidStaffAssignmentError,
    InvalidStatusTransitionError,
    TooManyAttachmentsError,
    UnsupportedFileTypeError,
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
async def other_citizen(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Other Citizen",
        email=f"pytest-other-{uuid.uuid4()}@example.com",
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


async def _make_resolved_complaint(db, citizen, admin, staff):
    """submitted -> approved -> assigned to staff -> in_progress -> resolved."""
    complaint = await _make_complaint(db, citizen)
    await transition_complaint_status(complaint.id, "approve", admin, None, db)
    complaint.assigned_to = staff.id
    await db.flush()
    await transition_complaint_status(complaint.id, "start", staff, None, db)
    return await transition_complaint_status(complaint.id, "resolve", staff, "Fixed.", db)


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


class TestListMyComplaints:
    async def test_returns_only_the_calling_citizens_own_complaints(self, db, citizen):
        # The one property GET /complaints/mine must never get wrong:
        # a citizen's own list must never include another citizen's
        # complaint, whatever else changes about this endpoint.
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        mine = await _make_complaint(db, citizen)
        theirs = await _make_complaint(db, other)

        result = await list_my_complaints(citizen.id, db)

        assert [c.id for c in result] == [mine.id]
        assert theirs.id not in [c.id for c in result]

        await _cleanup(db, mine)
        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_ordered_newest_first(self, db, citizen):
        older = await _make_complaint(db, citizen)
        # created_at is server-side now(), which in Postgres is the
        # *transaction's* start time, not per-statement wall-clock time,
        # so two inserts in the same uncommitted transaction would get
        # an identical created_at and make this test meaningless.
        # Committing here forces a real transaction boundary between
        # the two complaints, matching how two separate POST /complaints
        # requests behave in production (each gets its own transaction).
        await db.commit()
        newer = await _make_complaint(db, citizen)

        result = await list_my_complaints(citizen.id, db)

        result_ids = [c.id for c in result]
        assert result_ids.index(newer.id) < result_ids.index(older.id)

        await _cleanup(db, older)
        await _cleanup(db, newer)

    async def test_empty_for_a_citizen_with_no_complaints(self, db, citizen):
        result = await list_my_complaints(citizen.id, db)
        assert result == []


class TestListComplaints:
    async def test_citizen_only_sees_their_own_complaints(self, db, citizen):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        mine = await _make_complaint(db, citizen)
        theirs = await _make_complaint(db, other)

        results, total = await list_complaints(citizen, db)

        assert [c.id for c in results] == [mine.id]
        assert total == 1

        await _cleanup(db, mine)
        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_admin_sees_every_citizens_complaints(self, db, citizen, admin):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        mine = await _make_complaint(db, citizen)
        theirs = await _make_complaint(db, other)

        results, total = await list_complaints(admin, db, per_page=1000)

        result_ids = {c.id for c in results}
        assert mine.id in result_ids
        assert theirs.id in result_ids
        assert total >= 2

        await _cleanup(db, mine)
        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_filters_by_category(self, db, citizen, admin):
        pothole = await _make_complaint(db, citizen)
        garbage_data = ComplaintCreate(
            title="Overflowing garbage bin",
            description="Garbage has not been collected in over a week near the market.",
            category="garbage",
            location=ComplaintLocation(address="Dadar Market, Mumbai"),
        )
        garbage = await create_complaint(citizen.id, garbage_data, db)

        results, total = await list_complaints(admin, db, category="garbage", per_page=1000)

        result_ids = {c.id for c in results}
        assert garbage.id in result_ids
        assert pothole.id not in result_ids

        await _cleanup(db, pothole)
        await _cleanup(db, garbage)

    async def test_filters_by_status(self, db, citizen, admin):
        submitted = await _make_complaint(db, citizen)
        approved = await _make_complaint(db, citizen)
        await transition_complaint_status(approved.id, "approve", admin, None, db)
        await db.commit()

        results, total = await list_complaints(admin, db, status="approved", per_page=1000)

        result_ids = {c.id for c in results}
        assert approved.id in result_ids
        assert submitted.id not in result_ids

        await _cleanup(db, submitted)
        await _cleanup(db, approved)

    async def test_pagination_respects_page_and_per_page(self, db, citizen):
        first = await _make_complaint(db, citizen)
        await db.commit()
        second = await _make_complaint(db, citizen)
        await db.commit()
        third = await _make_complaint(db, citizen)

        page_one, total = await list_complaints(citizen, db, page=1, per_page=2)
        page_two, _ = await list_complaints(citizen, db, page=2, per_page=2)

        assert total == 3
        assert len(page_one) == 2
        assert len(page_two) == 1
        assert {c.id for c in page_one} | {c.id for c in page_two} == {first.id, second.id, third.id}

        await _cleanup(db, first)
        await _cleanup(db, second)
        await _cleanup(db, third)

    async def test_sort_by_priority_score_ascending(self, db, citizen):
        first = await _make_complaint(db, citizen)
        second = await _make_complaint(db, citizen)

        results, _ = await list_complaints(
            citizen, db, sort_by="priority_score", order="asc", per_page=1000
        )
        result_ids = [c.id for c in results]

        scores = [c.priority_score for c in results if c.id in {first.id, second.id}]
        assert scores == sorted(scores)

        await _cleanup(db, first)
        await _cleanup(db, second)

    async def test_empty_for_a_citizen_with_no_complaints(self, db, citizen):
        results, total = await list_complaints(citizen, db)
        assert results == []
        assert total == 0


class TestExportComplaintsCsv:
    async def test_includes_a_real_complaint_with_resolved_names(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await db.commit()

        csv_text = await export_complaints_csv(admin, db)
        rows = list(csv.reader(io.StringIO(csv_text)))

        assert rows[0] == [
            "id", "title", "category", "status", "priority_score",
            "location_text", "ward_code", "citizen_name", "assigned_to_name",
            "created_at", "updated_at",
        ]
        matching = [r for r in rows[1:] if r[0] == str(complaint.id)]
        assert len(matching) == 1
        # citizen_name (index 7) should be the real name, not a raw UUID.
        assert matching[0][7] == citizen.name

        await _cleanup(db, complaint)

    async def test_filters_by_status(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        csv_text = await export_complaints_csv(admin, db, status="approved")
        rows = list(csv.reader(io.StringIO(csv_text)))

        assert all(r[3] == "approved" for r in rows[1:])
        assert any(r[0] == str(complaint.id) for r in rows[1:])

        await _cleanup(db, complaint)

    async def test_citizen_only_sees_their_own_complaints(self, db, citizen, other_citizen):
        mine = await _make_complaint(db, citizen)
        theirs = await _make_complaint(db, other_citizen)
        await db.commit()

        csv_text = await export_complaints_csv(citizen, db)
        rows = list(csv.reader(io.StringIO(csv_text)))
        ids = {r[0] for r in rows[1:]}

        assert str(mine.id) in ids
        assert str(theirs.id) not in ids

        await _cleanup(db, mine)
        await _cleanup(db, theirs)

    async def test_defuses_a_formula_injection_attempt_in_the_title(self, db, citizen, admin):
        # title is citizen-controlled free text with no character
        # restriction, a title starting with '=' would run as a live
        # formula the moment an admin opens the export in Excel/Sheets
        # (CWE-1236) unless it's neutralized first.
        data = ComplaintCreate(
            title='=HYPERLINK("http://evil.example","click")',
            description="This description is long enough to satisfy the minimum length rule.",
            category="pothole",
            location=ComplaintLocation(address="Near Patel Chowk, Patan"),
        )
        complaint = await create_complaint(citizen.id, data, db)
        await db.commit()

        csv_text = await export_complaints_csv(admin, db)
        rows = list(csv.reader(io.StringIO(csv_text)))
        matching = [r for r in rows[1:] if r[0] == str(complaint.id)]

        assert len(matching) == 1
        assert matching[0][1].startswith("'=")

        await _cleanup(db, complaint)


class TestGetComplaintDetail:
    async def test_owner_citizen_can_view_their_own_complaint(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        result, staff = await get_complaint_detail(complaint.id, citizen, db)

        assert result.id == complaint.id
        assert staff is None

        await _cleanup(db, complaint)

    async def test_citizen_cannot_view_someone_elses_complaint(self, db, citizen):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        theirs = await _make_complaint(db, other)

        with pytest.raises(ComplaintNotOwnerError):
            await get_complaint_detail(theirs.id, citizen, db)

        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_admin_can_view_any_complaint(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)

        result, staff = await get_complaint_detail(complaint.id, admin, db)

        assert result.id == complaint.id
        assert staff is None

        await _cleanup(db, complaint)

    async def test_staff_can_view_any_complaint(self, db, citizen, staff):
        complaint = await _make_complaint(db, citizen)

        result, assigned_staff = await get_complaint_detail(complaint.id, staff, db)

        assert result.id == complaint.id
        assert assigned_staff is None

        await _cleanup(db, complaint)

    async def test_returns_assigned_staff_member(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        await assign_complaint(complaint.id, admin.id, ComplaintAssignRequest(assigned_to=staff.id), db)
        await db.commit()

        result, assigned_staff = await get_complaint_detail(complaint.id, citizen, db)

        assert assigned_staff is not None
        assert assigned_staff.id == staff.id

        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_complaint(self, db, admin):
        with pytest.raises(ComplaintNotFoundError):
            await get_complaint_detail(uuid.uuid4(), admin, db)


class TestListComplaintsByWard:
    async def test_returns_only_complaints_in_that_ward(self, db, citizen):
        in_ward = await create_complaint(
            citizen.id,
            ComplaintCreate(
                title="Pothole outside Colaba station",
                description="A large pothole has formed right outside the station entrance.",
                category="pothole",
                location=ComplaintLocation(address="Colaba Causeway, Mumbai"),
                ward_code="A",
            ),
            db,
        )
        elsewhere = await _make_complaint(db, citizen)

        results = await list_complaints_by_ward("A", db)

        result_ids = {c.id for c in results}
        assert in_ward.id in result_ids
        assert elsewhere.id not in result_ids

        await _cleanup(db, in_ward)
        await _cleanup(db, elsewhere)

    async def test_only_returns_complaints_for_the_given_ward_code(self, db, citizen):
        # A fresh, unlikely-to-collide ward code rather than asserting a
        # truly empty result, other tests in the suite may run
        # concurrently and leave complaints in commonly-used wards.
        results = await list_complaints_by_ward("Z-UNUSED", db)
        assert results == []


class TestListComplaintsByCategory:
    async def test_returns_only_complaints_in_that_category(self, db, citizen):
        pothole = await _make_complaint(db, citizen)
        garbage = await create_complaint(
            citizen.id,
            ComplaintCreate(
                title="Overflowing garbage bin",
                description="Garbage has not been collected in over a week near the market.",
                category="garbage",
                location=ComplaintLocation(address="Dadar Market, Mumbai"),
            ),
            db,
        )

        results = await list_complaints_by_category("garbage", db)

        result_ids = {c.id for c in results}
        assert garbage.id in result_ids
        assert pothole.id not in result_ids

        await _cleanup(db, pothole)
        await _cleanup(db, garbage)


class TestGetComplaintHistory:
    async def test_owner_citizen_sees_status_changes_only(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await add_complaint_note(complaint.id, admin.id, "Just a note, not a status change.", db)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        history = await get_complaint_history(complaint.id, citizen, db)

        assert len(history) == 1
        change, changer = history[0]
        assert change.old_status == "submitted"
        assert change.new_status == "approved"
        assert changer.id == admin.id

        await _cleanup(db, complaint)

    async def test_citizen_cannot_view_someone_elses_history(self, db, citizen):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        theirs = await _make_complaint(db, other)

        with pytest.raises(ComplaintNotOwnerError):
            await get_complaint_history(theirs.id, citizen, db)

        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_admin_can_view_any_complaints_history(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        history = await get_complaint_history(complaint.id, admin, db)

        assert len(history) == 1

        await _cleanup(db, complaint)

    async def test_empty_for_a_complaint_with_no_status_changes_yet(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        history = await get_complaint_history(complaint.id, citizen, db)

        assert history == []

        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_complaint(self, db, admin):
        with pytest.raises(ComplaintNotFoundError):
            await get_complaint_history(uuid.uuid4(), admin, db)


class TestListComplaintAttachments:
    async def test_empty_list_when_nothing_uploaded(self, db, citizen):
        # There is no upload endpoint yet, so this is the only state
        # every complaint can actually be in today, that's expected.
        complaint = await _make_complaint(db, citizen)

        attachments = await list_complaint_attachments(complaint.id, citizen, db)

        assert attachments == []

        await _cleanup(db, complaint)

    async def test_owner_citizen_can_list_their_own(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        attachments = await list_complaint_attachments(complaint.id, citizen, db)

        assert attachments == []

        await _cleanup(db, complaint)

    async def test_citizen_cannot_list_someone_elses(self, db, citizen):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        theirs = await _make_complaint(db, other)

        with pytest.raises(ComplaintNotOwnerError):
            await list_complaint_attachments(theirs.id, citizen, db)

        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_admin_can_list_any(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)

        attachments = await list_complaint_attachments(complaint.id, admin, db)

        assert attachments == []

        await _cleanup(db, complaint)

    async def test_staff_can_list_any(self, db, citizen, staff):
        complaint = await _make_complaint(db, citizen)

        attachments = await list_complaint_attachments(complaint.id, staff, db)

        assert attachments == []

        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_complaint(self, db, admin):
        with pytest.raises(ComplaintNotFoundError):
            await list_complaint_attachments(uuid.uuid4(), admin, db)

    async def test_lists_real_rows_when_present(self, db, citizen):
        # No upload endpoint exists yet to create these through the API,
        # so this test inserts ComplaintImage rows directly, the same
        # way test_pure_status_change_rows_are_not_listed_as_notes above
        # reaches into ComplaintUpdate directly for a case the service
        # layer alone can't set up.
        complaint = await _make_complaint(db, citizen)
        older = ComplaintImage(complaint_id=complaint.id, image_url="https://example.com/a.jpg")
        db.add(older)
        await db.flush()
        await db.commit()
        newer = ComplaintImage(complaint_id=complaint.id, image_url="https://example.com/b.jpg")
        db.add(newer)
        await db.flush()

        attachments = await list_complaint_attachments(complaint.id, citizen, db)

        assert [a.id for a in attachments] == [older.id, newer.id]

        await db.delete(older)
        await db.delete(newer)
        await _cleanup(db, complaint)


# Real magic bytes for a couple of allowed types, validate_upload now
# checks actual file content against these, not just the client's
# claimed Content-Type, so a test can no longer get away with
# b"fake-jpeg-bytes" for "image/jpeg", it has to actually start with
# what a real JPEG/PNG starts with.
JPEG_MAGIC_BYTES = b"\xff\xd8\xff" + b"fake-rest-of-file"
PNG_MAGIC_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-rest-of-file"


class TestUploadComplaintAttachment:
    async def test_owner_citizen_can_upload_to_own_complaint(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        attachment = await upload_complaint_attachment(
            complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db
        )
        await db.commit()

        assert attachment.complaint_id == complaint.id
        assert attachment.image_url.startswith(f"/{settings.UPLOAD_DIR}/complaints/{complaint.id}/")
        assert attachment.image_url.endswith(".jpg")

        await db.delete(attachment)
        await _cleanup(db, complaint)

    async def test_citizen_cannot_upload_to_someone_elses_complaint(self, db, citizen):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        theirs = await _make_complaint(db, other)

        with pytest.raises(ComplaintNotOwnerError):
            await upload_complaint_attachment(theirs.id, citizen, "image/jpeg", b"data", db)

        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_admin_can_upload_to_any_complaint(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)

        attachment = await upload_complaint_attachment(
            complaint.id, admin, "application/pdf", b"%PDF-fake", db
        )
        await db.commit()

        assert attachment.image_url.endswith(".pdf")

        await db.delete(attachment)
        await _cleanup(db, complaint)

    async def test_staff_can_upload_to_any_complaint(self, db, citizen, staff):
        complaint = await _make_complaint(db, citizen)

        attachment = await upload_complaint_attachment(
            complaint.id, staff, "image/png", PNG_MAGIC_BYTES, db
        )
        await db.commit()

        assert attachment.image_url.endswith(".png")

        await db.delete(attachment)
        await _cleanup(db, complaint)

    async def test_rejects_unsupported_file_type(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        with pytest.raises(UnsupportedFileTypeError):
            await upload_complaint_attachment(
                complaint.id, citizen, "application/x-msdownload", b"data", db
            )

        await _cleanup(db, complaint)

    async def test_rejects_content_that_does_not_match_the_claimed_type(self, db, citizen):
        # A client can claim any allowed Content-Type it wants, this
        # confirms the actual bytes are checked too, not just the
        # header, PNG magic bytes labeled as a JPEG should still be
        # rejected.
        complaint = await _make_complaint(db, citizen)

        with pytest.raises(UnsupportedFileTypeError):
            await upload_complaint_attachment(complaint.id, citizen, "image/jpeg", PNG_MAGIC_BYTES, db)

        await _cleanup(db, complaint)

    async def test_rejects_a_file_over_the_size_limit(self, db, citizen):
        complaint = await _make_complaint(db, citizen)
        oversized = b"x" * (settings.MAX_UPLOAD_SIZE_BYTES + 1)

        with pytest.raises(FileTooLargeError):
            await upload_complaint_attachment(complaint.id, citizen, "image/jpeg", oversized, db)

        await _cleanup(db, complaint)

    async def test_rejects_uploading_past_the_per_complaint_limit(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        for _ in range(settings.MAX_ATTACHMENTS_PER_COMPLAINT):
            await upload_complaint_attachment(complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db)
            await db.commit()

        with pytest.raises(TooManyAttachmentsError):
            await upload_complaint_attachment(complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db)

        result = await db.execute(
            select(ComplaintImage).where(ComplaintImage.complaint_id == complaint.id)
        )
        for a in result.scalars().all():
            await db.delete(a)
        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_complaint(self, db, admin):
        with pytest.raises(ComplaintNotFoundError):
            await upload_complaint_attachment(uuid.uuid4(), admin, "image/jpeg", b"data", db)

    async def test_defaults_to_citizen_evidence_purpose(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        attachment = await upload_complaint_attachment(
            complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db
        )
        await db.commit()

        assert attachment.purpose == "citizen_evidence"

        await db.delete(attachment)
        await _cleanup(db, complaint)


class TestUploadResolutionProofAttachment:
    async def test_assigned_staff_can_upload_once_resolved(self, db, citizen, admin, staff):
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)

        attachment = await upload_complaint_attachment(
            complaint.id, staff, "image/jpeg", JPEG_MAGIC_BYTES, db, purpose="resolution_proof"
        )
        await db.commit()

        assert attachment.purpose == "resolution_proof"

        await db.delete(attachment)
        await _cleanup(db, complaint)

    async def test_admin_can_upload_regardless_of_assignment(self, db, citizen, admin, staff):
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)

        attachment = await upload_complaint_attachment(
            complaint.id, admin, "image/jpeg", JPEG_MAGIC_BYTES, db, purpose="resolution_proof"
        )
        await db.commit()

        assert attachment.purpose == "resolution_proof"

        await db.delete(attachment)
        await _cleanup(db, complaint)

    async def test_rejects_a_citizen_uploading_resolution_proof(self, db, citizen, admin, staff):
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)

        with pytest.raises(InsufficientPermissionsError):
            await upload_complaint_attachment(
                complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db, purpose="resolution_proof"
            )

        await _cleanup(db, complaint)

    async def test_rejects_before_the_complaint_is_resolved(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        complaint.assigned_to = staff.id
        await db.flush()
        await transition_complaint_status(complaint.id, "start", staff, None, db)

        with pytest.raises(ComplaintNotResolvedError):
            await upload_complaint_attachment(
                complaint.id, staff, "image/jpeg", JPEG_MAGIC_BYTES, db, purpose="resolution_proof"
            )

        await _cleanup(db, complaint)

    async def test_rejects_staff_not_assigned_to_the_complaint(self, db, citizen, admin, staff):
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)

        other_staff = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Staff",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="staff",
            hashed_password="x",
            is_active=True,
        )
        db.add(other_staff)
        await db.flush()

        with pytest.raises(ComplaintNotAssignedToUserError):
            await upload_complaint_attachment(
                complaint.id, other_staff, "image/jpeg", JPEG_MAGIC_BYTES, db, purpose="resolution_proof"
            )

        await db.delete(other_staff)
        await _cleanup(db, complaint)


class TestEditComplaint:
    async def test_owner_citizen_can_edit_title_and_description(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        edited = await edit_complaint(
            complaint.id, citizen, "Updated title here", "Updated description with enough length.", db
        )
        await db.commit()

        assert edited.title == "Updated title here"
        assert edited.description == "Updated description with enough length."

        await _cleanup(db, complaint)

    async def test_can_edit_just_one_field(self, db, citizen):
        complaint = await _make_complaint(db, citizen)
        original_description = complaint.description

        edited = await edit_complaint(complaint.id, citizen, "New title only", None, db)
        await db.commit()

        assert edited.title == "New title only"
        assert edited.description == original_description

        await _cleanup(db, complaint)

    async def test_citizen_cannot_edit_someone_elses_complaint(self, db, citizen):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        theirs = await _make_complaint(db, other)

        with pytest.raises(ComplaintNotOwnerError):
            await edit_complaint(theirs.id, citizen, "Hijacked title", None, db)

        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_staff_cannot_edit_a_complaint(self, db, citizen, staff):
        # No route-level bypass check here since require_roles(ROLE_CITIZEN)
        # already keeps staff out at the route layer, this confirms the
        # service's own ownership check independently rejects a staff
        # caller too, staff.id never matches complaint.citizen_id.
        complaint = await _make_complaint(db, citizen)

        with pytest.raises(ComplaintNotOwnerError):
            await edit_complaint(complaint.id, staff, "Staff edit attempt", None, db)

        await _cleanup(db, complaint)

    async def test_cannot_edit_after_approval(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        with pytest.raises(InvalidStatusTransitionError):
            await edit_complaint(complaint.id, citizen, "Too late now", None, db)

        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_complaint(self, db, citizen):
        with pytest.raises(ComplaintNotFoundError):
            await edit_complaint(uuid.uuid4(), citizen, "Doesn't matter", None, db)


class TestDeleteComplaint:
    async def test_admin_can_delete_a_complaint(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        complaint_id = complaint.id
        await db.commit()

        await delete_complaint(complaint_id, db)
        await db.commit()

        assert await db.get(Complaint, complaint_id) is None

    async def test_delete_cascades_to_notes(self, db, citizen, staff):
        complaint = await _make_complaint(db, citizen)
        await add_complaint_note(complaint.id, staff.id, "A note that should vanish with the complaint.", db)
        await db.commit()
        complaint_id = complaint.id

        await delete_complaint(complaint_id, db)
        await db.commit()

        result = await db.execute(
            select(ComplaintUpdate).where(ComplaintUpdate.complaint_id == complaint_id)
        )
        assert result.scalars().all() == []

    async def test_delete_detaches_but_preserves_chat_sessions(self, db, citizen):
        # ChatSession.complaint_id has no ondelete configured at the
        # database level (unlike ComplaintUpdate/ComplaintImage/Rating,
        # which cascade), this is the one delete_complaint has to
        # handle itself, confirms it does: the session row survives,
        # just detached.
        complaint = await _make_complaint(db, citizen)
        session = ChatSession(
            session_id=f"pytest-session-{uuid.uuid4()}",
            user_id=citizen.id,
            complaint_id=complaint.id,
            role="assistant",
            message="Your complaint has been filed.",
        )
        db.add(session)
        await db.flush()
        await db.commit()
        session_id = session.id
        complaint_id = complaint.id

        await delete_complaint(complaint_id, db)
        await db.commit()

        refreshed = await db.get(ChatSession, session_id)
        assert refreshed is not None
        assert refreshed.complaint_id is None

        await db.delete(refreshed)
        await db.commit()

    async def test_rejects_a_nonexistent_complaint(self, db):
        with pytest.raises(ComplaintNotFoundError):
            await delete_complaint(uuid.uuid4(), db)


class TestWithdrawComplaint:
    async def test_owner_citizen_can_withdraw_a_submitted_complaint(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        withdrawn = await transition_complaint_status_as_owner(complaint.id, "withdraw", citizen, db)
        await db.commit()

        assert withdrawn.status == "withdrawn"

        await _cleanup(db, complaint)

    async def test_citizen_cannot_withdraw_someone_elses_complaint(self, db, citizen):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        theirs = await _make_complaint(db, other)

        with pytest.raises(ComplaintNotOwnerError):
            await transition_complaint_status_as_owner(theirs.id, "withdraw", citizen, db)

        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_cannot_withdraw_an_approved_complaint(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        with pytest.raises(InvalidStatusTransitionError):
            await transition_complaint_status_as_owner(complaint.id, "withdraw", citizen, db)

        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_complaint(self, db, citizen):
        with pytest.raises(ComplaintNotFoundError):
            await transition_complaint_status_as_owner(uuid.uuid4(), "withdraw", citizen, db)


class TestCloseComplaint:
    async def test_owner_citizen_can_close_a_resolved_complaint(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        complaint.assigned_to = staff.id
        await db.flush()
        await transition_complaint_status(complaint.id, "start", staff, None, db)
        await transition_complaint_status(complaint.id, "resolve", staff, "Fixed.", db)
        await db.commit()

        closed = await transition_complaint_status_as_owner(complaint.id, "close", citizen, db)
        await db.commit()

        assert closed.status == "closed"

        await _cleanup(db, complaint)

    async def test_citizen_cannot_close_someone_elses_complaint(self, db, citizen, admin, staff):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        theirs = await _make_complaint(db, other)
        await transition_complaint_status(theirs.id, "approve", admin, None, db)
        theirs.assigned_to = staff.id
        await db.flush()
        await transition_complaint_status(theirs.id, "start", staff, None, db)
        await transition_complaint_status(theirs.id, "resolve", staff, "Fixed.", db)
        await db.commit()

        with pytest.raises(ComplaintNotOwnerError):
            await transition_complaint_status_as_owner(theirs.id, "close", citizen, db)

        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_cannot_close_a_complaint_that_isnt_resolved(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        with pytest.raises(InvalidStatusTransitionError):
            await transition_complaint_status_as_owner(complaint.id, "close", citizen, db)

        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_complaint(self, db, citizen):
        with pytest.raises(ComplaintNotFoundError):
            await transition_complaint_status_as_owner(uuid.uuid4(), "close", citizen, db)


async def _resolve_and_backdate(db, citizen, admin, staff, days_ago):
    """
    Files a complaint through to 'resolved', then backdates the
    ComplaintUpdate row that recorded that resolve transition, so the
    auto-close job sees it as having sat there for `days_ago` days.
    create_complaint/transition_complaint_status don't accept a
    created_at override (correctly, a real caller never should), this
    reaches past them directly at the DB layer, test-only.
    """
    complaint = await _make_complaint(db, citizen)
    await transition_complaint_status(complaint.id, "approve", admin, None, db)
    complaint.assigned_to = staff.id
    await db.flush()
    await transition_complaint_status(complaint.id, "start", staff, None, db)
    await transition_complaint_status(complaint.id, "resolve", staff, "Fixed.", db)
    await db.commit()

    await db.execute(
        update(ComplaintUpdate)
        .where(ComplaintUpdate.complaint_id == complaint.id, ComplaintUpdate.new_status == "resolved")
        .values(created_at=datetime.utcnow() - timedelta(days=days_ago))
    )
    await db.commit()

    return complaint


class TestAutoCloseStaleResolvedComplaints:
    async def test_closes_a_complaint_resolved_more_than_7_days_ago(self, db, citizen, admin, staff):
        complaint = await _resolve_and_backdate(db, citizen, admin, staff, AUTO_CLOSE_AFTER_DAYS + 1)

        closed_count = await auto_close_stale_resolved_complaints(db)

        await db.refresh(complaint)
        assert complaint.status == "closed"
        assert closed_count >= 1

        result = await db.execute(
            select(Notification).where(
                Notification.complaint_id == complaint.id,
                Notification.user_id == citizen.id,
                Notification.type == "complaint_auto_closed",
            )
        )
        assert result.scalar_one_or_none() is not None

        result = await db.execute(
            select(Notification).where(
                Notification.complaint_id == complaint.id,
                Notification.user_id == staff.id,
                Notification.type == "complaint_closed",
            )
        )
        assert result.scalar_one_or_none() is not None

        await _cleanup(db, complaint)

    async def test_leaves_a_recently_resolved_complaint_alone(self, db, citizen, admin, staff):
        complaint = await _resolve_and_backdate(db, citizen, admin, staff, 1)

        await auto_close_stale_resolved_complaints(db)

        await db.refresh(complaint)
        assert complaint.status == "resolved"

        await _cleanup(db, complaint)

    async def test_does_not_touch_a_complaint_already_closed_by_the_citizen(self, db, citizen, admin, staff):
        complaint = await _resolve_and_backdate(db, citizen, admin, staff, AUTO_CLOSE_AFTER_DAYS + 1)
        await transition_complaint_status_as_owner(complaint.id, "close", citizen, db)
        await db.commit()

        closed_count = await auto_close_stale_resolved_complaints(db)

        await db.refresh(complaint)
        assert complaint.status == "closed"
        # It was already closed by the citizen, not by this job, this
        # complaint specifically shouldn't be counted as newly closed.
        result = await db.execute(
            select(ComplaintUpdate).where(
                ComplaintUpdate.complaint_id == complaint.id,
                ComplaintUpdate.notes.ilike("Auto-closed%"),
            )
        )
        assert result.scalar_one_or_none() is None

        await _cleanup(db, complaint)


class TestGetAttachment:
    async def test_owner_citizen_can_get_their_own_attachment(self, db, citizen):
        complaint = await _make_complaint(db, citizen)
        attachment = await upload_complaint_attachment(
            complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db
        )
        await db.commit()

        fetched = await get_attachment(attachment.id, citizen, db)

        assert fetched.id == attachment.id
        assert fetched.image_url == attachment.image_url

        await db.delete(attachment)
        await _cleanup(db, complaint)

    async def test_citizen_cannot_get_someone_elses_attachment(self, db, citizen):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        theirs = await _make_complaint(db, other)
        attachment = await upload_complaint_attachment(
            theirs.id, other, "image/jpeg", JPEG_MAGIC_BYTES, db
        )
        await db.commit()

        with pytest.raises(ComplaintNotOwnerError):
            await get_attachment(attachment.id, citizen, db)

        await db.delete(attachment)
        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_admin_can_get_any_attachment(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        attachment = await upload_complaint_attachment(
            complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db
        )
        await db.commit()

        fetched = await get_attachment(attachment.id, admin, db)

        assert fetched.id == attachment.id

        await db.delete(attachment)
        await _cleanup(db, complaint)

    async def test_staff_can_get_any_attachment(self, db, citizen, staff):
        complaint = await _make_complaint(db, citizen)
        attachment = await upload_complaint_attachment(
            complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db
        )
        await db.commit()

        fetched = await get_attachment(attachment.id, staff, db)

        assert fetched.id == attachment.id

        await db.delete(attachment)
        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_attachment(self, db, admin):
        with pytest.raises(AttachmentNotFoundError):
            await get_attachment(uuid.uuid4(), admin, db)


class TestDeleteAttachment:
    async def test_owner_citizen_can_delete_their_own_attachment(self, db, citizen):
        complaint = await _make_complaint(db, citizen)
        attachment = await upload_complaint_attachment(
            complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db
        )
        await db.commit()
        attachment_id = attachment.id

        await delete_attachment(attachment_id, citizen, db)
        await db.commit()

        assert await db.get(ComplaintImage, attachment_id) is None

        await _cleanup(db, complaint)

    async def test_citizen_cannot_delete_someone_elses_attachment(self, db, citizen):
        other = User(
            phone=f"9{uuid.uuid4().int % 10**9:09d}",
            name="Pytest Other Citizen",
            email=f"pytest-{uuid.uuid4()}@example.com",
            role="citizen",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        await db.flush()

        theirs = await _make_complaint(db, other)
        attachment = await upload_complaint_attachment(
            theirs.id, other, "image/jpeg", JPEG_MAGIC_BYTES, db
        )
        await db.commit()

        with pytest.raises(ComplaintNotOwnerError):
            await delete_attachment(attachment.id, citizen, db)

        await db.delete(attachment)
        await _cleanup(db, theirs)
        await db.delete(other)
        await db.commit()

    async def test_staff_cannot_delete_an_attachment(self, db, citizen, staff):
        # Unlike list/upload, the design doc lists delete as
        # Citizen (own)/Admin only, staff is deliberately excluded.
        complaint = await _make_complaint(db, citizen)
        attachment = await upload_complaint_attachment(
            complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db
        )
        await db.commit()

        with pytest.raises(ComplaintNotOwnerError):
            await delete_attachment(attachment.id, staff, db)

        await db.delete(attachment)
        await _cleanup(db, complaint)

    async def test_admin_can_delete_any_attachment(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        attachment = await upload_complaint_attachment(
            complaint.id, citizen, "image/jpeg", JPEG_MAGIC_BYTES, db
        )
        await db.commit()
        attachment_id = attachment.id

        await delete_attachment(attachment_id, admin, db)
        await db.commit()

        assert await db.get(ComplaintImage, attachment_id) is None

        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_attachment(self, db, admin):
        with pytest.raises(AttachmentNotFoundError):
            await delete_attachment(uuid.uuid4(), admin, db)
