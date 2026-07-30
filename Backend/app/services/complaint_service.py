"""
Complaint submission (#41) and internal notes.

Creates a real Complaint row from a citizen's POST /complaints request,
then immediately runs it through the same ML pipeline the /ml/* routes
already expose individually (priority scoring, department routing,
high-risk flagging), so a freshly filed complaint doesn't sit with a
meaningless priority_score=0/no department until someone separately
calls those endpoints. Reuses those exact services rather than
duplicating any scoring/routing logic here.
"""

from sqlalchemy import select

from app.model import Complaint, ComplaintUpdate, User
from app.schemas.complaint import ComplaintCreate
from app.services.priority_service import score_complaint
from app.services.risk_alert_service import flag_if_high_risk
from app.services.routing_service import route_complaint
from app.utils.exceptions import ComplaintNotFoundError


def _location_text(location) -> str:
    """
    Complaint.location_text is a single string column, there's no
    separate latitude/longitude storage on Complaint yet. Prefer the
    human-readable address when given; fall back to formatting the
    coordinates so location isn't silently dropped when only a pin (no
    address) was provided.
    """
    if location.address and location.address.strip():
        return location.address.strip()
    return f"{location.latitude}, {location.longitude}"


async def create_complaint(citizen_id, data: ComplaintCreate, db) -> Complaint:
    """
    Creates the complaint, then scores and routes it immediately using
    the already-existing ML services, same pattern app/api/ml.py's
    individual endpoints use. Does not commit, callers (the route, via
    get_db) are responsible for that, same convention as every other
    service in this app.
    """
    complaint = Complaint(
        citizen_id=citizen_id,
        title=data.title,
        description=data.description,
        category=data.category.value,
        location_text=_location_text(data.location),
    )
    db.add(complaint)
    await db.flush()

    complaint.priority_score = round(await score_complaint(complaint, db))

    department = await route_complaint(complaint, db)
    complaint.department_id = department.id if department else None

    await flag_if_high_risk(complaint, db)

    return complaint


async def add_complaint_note(
    complaint_id,
    author_id,
    note_text: str,
    db,
) -> tuple[ComplaintUpdate, User]:
    """
    Adds an internal note to a complaint, stored as a ComplaintUpdate
    row with old_status/new_status left null (a pure note, no status
    change attached). Returns (note, author) for the same reason
    assign_complaint returns (complaint, staff): the route needs the
    author's name/role to build ComplaintNoteAuthor, and re-fetching
    the author a second time in the route would be redundant.

    Does not commit, same convention as create_complaint above.
    """
    complaint = await db.get(Complaint, complaint_id)
    if complaint is None:
        raise ComplaintNotFoundError("Complaint not found.")

    author = await db.get(User, author_id)

    note = ComplaintUpdate(
        complaint_id=complaint.id,
        updated_by=author_id,
        old_status=None,
        new_status=None,
        notes=note_text,
    )
    db.add(note)
    await db.flush()

    return note, author


async def list_complaint_notes(complaint_id, db) -> list[tuple[ComplaintUpdate, User]]:
    """
    Every internal note on a complaint, oldest first, each paired
    with its author. Only ComplaintUpdate rows that actually carry
    note text count as a "note" here, a pure status-change row with
    no commentary (notes IS NULL) isn't one.
    """
    complaint = await db.get(Complaint, complaint_id)
    if complaint is None:
        raise ComplaintNotFoundError("Complaint not found.")

    result = await db.execute(
        select(ComplaintUpdate)
        .where(ComplaintUpdate.complaint_id == complaint_id, ComplaintUpdate.notes.isnot(None))
        .order_by(ComplaintUpdate.created_at)
    )
    notes = result.scalars().all()

    author_ids = {note.updated_by for note in notes}
    authors_by_id = {}
    if author_ids:
        result = await db.execute(select(User).where(User.id.in_(author_ids)))
        authors_by_id = {user.id: user for user in result.scalars().all()}

    return [(note, authors_by_id.get(note.updated_by)) for note in notes]
