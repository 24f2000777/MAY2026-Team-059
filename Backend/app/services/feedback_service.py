"""
Feedback & Rating (section 9 of the API design doc). One rating per
complaint (Rating.complaint_id is unique, see app/model.py), only
submittable while the complaint is RESOLVED, and submitting it
auto-transitions the complaint to CLOSED, reusing
transition_complaint_status_as_owner's own "close" action rather than
duplicating that transition logic here.
"""

from sqlalchemy import func as sa_func
from sqlalchemy import select

from app.model import Complaint, Rating, User
from app.schemas.complaint import ComplaintStatus
from app.services.complaint_service import _get_visible_complaint, transition_complaint_status_as_owner
from app.utils.exceptions import (
    ComplaintNotFoundError,
    ComplaintNotOwnerError,
    ComplaintNotResolvedError,
    RatingAlreadyExistsError,
)


async def submit_feedback(complaint_id, citizen, score: int, feedback_text, db) -> Rating:
    """
    Backs POST /complaints/{id}/feedback. Citizen-and-owner-only, same
    as edit_complaint, staff/admin do not get a bypass here, per the
    design doc this is the citizen confirming their own experience.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        ComplaintNotOwnerError: 403, if the complaint isn't the
            caller's own.
        ComplaintNotResolvedError: 409, if the complaint isn't
            currently RESOLVED.
        RatingAlreadyExistsError: 409, if this complaint already has
            a rating.

    Does not commit, same convention as create_complaint above.
    """
    complaint = await db.get(Complaint, complaint_id)
    if complaint is None:
        raise ComplaintNotFoundError("Complaint not found.")

    if complaint.citizen_id != citizen.id:
        raise ComplaintNotOwnerError("You can only rate your own complaints.")

    if complaint.status != ComplaintStatus.RESOLVED.value:
        raise ComplaintNotResolvedError(
            f"Cannot submit feedback for a complaint that is currently '{complaint.status}'."
        )

    existing = await db.execute(select(Rating.id).where(Rating.complaint_id == complaint_id))
    if existing.first() is not None:
        raise RatingAlreadyExistsError("This complaint has already been rated.")

    rating = Rating(
        complaint_id=complaint_id,
        citizen_id=citizen.id,
        score=score,
        feedback=feedback_text,
    )
    db.add(rating)

    # Reuses the owner-close transition wholesale (state check, log
    # entry, and the staff notification it already sends), rather than
    # re-implementing "citizen confirms → CLOSED" a second time here.
    await transition_complaint_status_as_owner(complaint_id, "close", citizen, db)

    await db.flush()
    return rating


async def get_feedback(complaint_id, current_user, db) -> Rating | None:
    """
    Backs GET /complaints/{id}/feedback. Same ownership boundary as
    get_complaint_detail: a citizen can only see their own complaint's
    feedback, staff and admin can see any. Returns None (not a 404) if
    the complaint exists but has no rating yet, "no feedback" is a
    valid state, not an error.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        ComplaintNotOwnerError: 403, if a citizen requests a complaint
            that isn't theirs.
    """
    await _get_visible_complaint(complaint_id, current_user, db)

    result = await db.execute(select(Rating).where(Rating.complaint_id == complaint_id))
    return result.scalar_one_or_none()


async def get_officer_ratings(staff_id, db) -> tuple[User, list[Rating], float | None]:
    """
    Backs GET /feedback/officer/{id}. Aggregates every rating left on
    a complaint the given staff member was assigned to at resolution
    time (Complaint.assigned_to at read time, there's no separate
    "resolved by" column). Returns (officer, ratings, average) so the
    route doesn't need a second round trip for the officer's name.

    Raises:
        UserNotFoundError is deliberately not raised for a
        nonexistent/non-staff id, an admin browsing by id that
        happens to not exist just sees zero ratings, same reasoning
        as an empty list being a valid result rather than an error
        elsewhere in this app.
    """
    officer = await db.get(User, staff_id)

    result = await db.execute(
        select(Rating)
        .join(Complaint, Complaint.id == Rating.complaint_id)
        .where(Complaint.assigned_to == staff_id)
        .order_by(Rating.created_at.desc())
    )
    ratings = result.scalars().all()

    average = sum(r.score for r in ratings) / len(ratings) if ratings else None

    return officer, ratings, average


async def get_feedback_summary(db) -> tuple[int, float | None, dict[int, int]]:
    """
    Backs GET /feedback/summary. Platform-wide, not scoped to any one
    officer or department, per the design doc.

    Returns (total, average, distribution) where distribution maps
    each star value 1-5 to how many ratings have it, always all 5
    keys present (zero-filled), so the route/UI never has to guard
    against a missing key for a score nobody's used yet.
    """
    result = await db.execute(select(Rating.score))
    scores = result.scalars().all()

    total = len(scores)
    average = sum(scores) / total if total else None
    distribution = {n: 0 for n in range(1, 6)}
    for score in scores:
        distribution[score] = distribution.get(score, 0) + 1

    return total, average, distribution
