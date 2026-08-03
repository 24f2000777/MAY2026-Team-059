"""
Pytest suite for the Feedback & Rating API's service layer (submit,
get, officer aggregation, platform summary).

Hits real Supabase, same reasoning as the other unmocked service
suites in this project.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.model import Complaint, ComplaintUpdate, Notification, Rating, User
from app.schemas.complaint import ComplaintAssignRequest, ComplaintCreate, ComplaintLocation
from app.services.complaint_service import assign_complaint, create_complaint, transition_complaint_status
from app.services.feedback_service import (
    get_feedback,
    get_feedback_summary,
    get_officer_ratings,
    submit_feedback,
)
from app.utils.exceptions import (
    ComplaintNotFoundError,
    ComplaintNotOwnerError,
    ComplaintNotResolvedError,
    RatingAlreadyExistsError,
)


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def citizen(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Feedback Citizen",
        email=f"pytest-feedback-{uuid.uuid4()}@example.com",
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
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Feedback Admin",
        email=f"pytest-feedback-admin-{uuid.uuid4()}@example.com",
        role="admin",
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
        name="Pytest Feedback Staff",
        email=f"pytest-feedback-staff-{uuid.uuid4()}@example.com",
        role="staff",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    yield user
    await db.delete(user)
    await db.commit()


async def _cleanup(db, complaint):
    result = await db.execute(select(Rating).where(Rating.complaint_id == complaint.id))
    for r in result.scalars().all():
        await db.delete(r)
    result = await db.execute(select(Notification).where(Notification.complaint_id == complaint.id))
    for n in result.scalars().all():
        await db.delete(n)
    result = await db.execute(select(ComplaintUpdate).where(ComplaintUpdate.complaint_id == complaint.id))
    for u in result.scalars().all():
        await db.delete(u)
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


async def _make_resolved_complaint(db, citizen, admin, staff):
    complaint = await _make_complaint(db, citizen)
    await assign_complaint(complaint.id, admin.id, ComplaintAssignRequest(assigned_to=staff.id), db)
    await transition_complaint_status(complaint.id, "approve", admin, None, db)
    await transition_complaint_status(complaint.id, "start", staff, None, db)
    await transition_complaint_status(complaint.id, "resolve", staff, None, db)
    await db.commit()
    return complaint


class TestSubmitFeedback:
    async def test_owner_citizen_can_submit_feedback(self, db, citizen, admin, staff):
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)

        rating = await submit_feedback(complaint.id, citizen, 5, "Great work!", db)
        await db.commit()

        assert rating.score == 5
        assert rating.feedback == "Great work!"
        assert rating.citizen_id == citizen.id

        await db.refresh(complaint)
        assert complaint.status == "closed"

        await _cleanup(db, complaint)

    async def test_rejects_feedback_on_a_non_resolved_complaint(self, db, citizen):
        complaint = await _make_complaint(db, citizen)

        with pytest.raises(ComplaintNotResolvedError):
            await submit_feedback(complaint.id, citizen, 4, None, db)

        await _cleanup(db, complaint)

    async def test_rejects_resubmission_once_already_closed(self, db, citizen, admin, staff):
        # Submitting feedback auto-closes the complaint, so a second
        # attempt hits the RESOLVED-only check before it could ever
        # reach the duplicate-rating guard, that guard exists purely
        # as defense in depth (see submit_feedback's docstring) for a
        # state this call sequence can't actually produce today.
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)
        await submit_feedback(complaint.id, citizen, 5, None, db)
        await db.commit()

        with pytest.raises(ComplaintNotResolvedError):
            await submit_feedback(complaint.id, citizen, 3, None, db)

        await _cleanup(db, complaint)

    async def test_rejects_a_rating_that_already_exists_even_if_still_resolved(self, db, citizen, admin, staff):
        # Exercises the duplicate-rating guard directly (bypassing the
        # normal auto-close coupling by inserting a Rating row and
        # manually resetting status back to "resolved"), since the
        # real call sequence above can never reach it, see that test's
        # comment.
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)
        db.add(Rating(complaint_id=complaint.id, citizen_id=citizen.id, score=5))
        await db.flush()

        with pytest.raises(RatingAlreadyExistsError):
            await submit_feedback(complaint.id, citizen, 3, None, db)

        await _cleanup(db, complaint)

    async def test_citizen_cannot_rate_someone_elses_complaint(self, db, citizen, admin, staff):
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

        complaint = await _make_resolved_complaint(db, other, admin, staff)

        with pytest.raises(ComplaintNotOwnerError):
            await submit_feedback(complaint.id, citizen, 5, None, db)

        await _cleanup(db, complaint)
        await db.delete(other)
        await db.commit()

    async def test_rejects_a_nonexistent_complaint(self, db, citizen):
        with pytest.raises(ComplaintNotFoundError):
            await submit_feedback(uuid.uuid4(), citizen, 5, None, db)


class TestGetFeedback:
    async def test_returns_none_when_not_yet_rated(self, db, citizen, admin, staff):
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)

        result = await get_feedback(complaint.id, citizen, db)

        assert result is None

        await _cleanup(db, complaint)

    async def test_owner_citizen_can_see_their_own_feedback(self, db, citizen, admin, staff):
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)
        await submit_feedback(complaint.id, citizen, 4, "Decent", db)
        await db.commit()

        result = await get_feedback(complaint.id, citizen, db)

        assert result is not None
        assert result.score == 4

        await _cleanup(db, complaint)

    async def test_admin_can_see_any_feedback(self, db, citizen, admin, staff):
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)
        await submit_feedback(complaint.id, citizen, 2, None, db)
        await db.commit()

        result = await get_feedback(complaint.id, admin, db)

        assert result is not None
        assert result.score == 2

        await _cleanup(db, complaint)

    async def test_citizen_cannot_see_someone_elses_feedback(self, db, citizen, admin, staff):
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

        complaint = await _make_resolved_complaint(db, other, admin, staff)
        await submit_feedback(complaint.id, other, 1, None, db)
        await db.commit()

        with pytest.raises(ComplaintNotOwnerError):
            await get_feedback(complaint.id, citizen, db)

        await _cleanup(db, complaint)
        await db.delete(other)
        await db.commit()

    async def test_rejects_a_nonexistent_complaint(self, db, admin):
        with pytest.raises(ComplaintNotFoundError):
            await get_feedback(uuid.uuid4(), admin, db)


class TestGetOfficerRatings:
    async def test_aggregates_ratings_for_the_officers_complaints(self, db, citizen, admin, staff):
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)
        await submit_feedback(complaint.id, citizen, 5, None, db)
        await db.commit()

        officer, ratings, average = await get_officer_ratings(staff.id, db)

        assert officer.id == staff.id
        assert len(ratings) >= 1
        assert any(r.complaint_id == complaint.id for r in ratings)
        assert average is not None

        await _cleanup(db, complaint)

    async def test_empty_for_an_officer_with_no_ratings(self, db, staff):
        officer, ratings, average = await get_officer_ratings(staff.id, db)

        assert officer.id == staff.id
        assert ratings == []
        assert average is None


class TestGetFeedbackSummary:
    async def test_includes_a_newly_submitted_rating(self, db, citizen, admin, staff):
        complaint = await _make_resolved_complaint(db, citizen, admin, staff)
        await submit_feedback(complaint.id, citizen, 3, None, db)
        await db.commit()

        total, average, distribution = await get_feedback_summary(db)

        assert total >= 1
        assert average is not None
        assert sum(distribution.values()) == total
        assert set(distribution.keys()) == {1, 2, 3, 4, 5}

        await _cleanup(db, complaint)
