"""
Complaint submission (#41) and the status state machine.

Creates a real Complaint row from a citizen's POST /complaints request,
then immediately runs it through the same ML pipeline the /ml/* routes
already expose individually (priority scoring, department routing,
high-risk flagging), so a freshly filed complaint doesn't sit with a
meaningless priority_score=0/no department until someone separately
calls those endpoints. Reuses those exact services rather than
duplicating any scoring/routing logic here.
"""

from app.model import Complaint, ComplaintUpdate
from app.schemas.complaint import ComplaintCreate, ComplaintStatus
from app.services.priority_service import score_complaint
from app.services.risk_alert_service import flag_if_high_risk
from app.services.routing_service import route_complaint
from app.utils.constants import ROLE_STAFF
from app.utils.exceptions import (
    ComplaintNotAssignedToUserError,
    ComplaintNotFoundError,
    InvalidStatusTransitionError,
)


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


# submitted --approve--> approved --start--> in_progress --resolve--> resolved
#     \                       \
#      \--reject--> rejected   \--reject--> rejected
#
# One table instead of four hand-written functions, since all four
# transitions really are the same shape: check the current status
# allows this move, optionally check assignment, set the new status,
# log it. requires_assignment gates both "must already be assigned"
# and "a staff caller must be that assignee" (see
# transition_complaint_status below).
TRANSITIONS = {
    "approve": {
        "from": {ComplaintStatus.SUBMITTED.value},
        "to": ComplaintStatus.APPROVED.value,
        "requires_assignment": False,
    },
    "reject": {
        "from": {ComplaintStatus.SUBMITTED.value, ComplaintStatus.APPROVED.value},
        "to": ComplaintStatus.REJECTED.value,
        "requires_assignment": False,
    },
    "start": {
        "from": {ComplaintStatus.APPROVED.value},
        "to": ComplaintStatus.IN_PROGRESS.value,
        "requires_assignment": True,
    },
    "resolve": {
        "from": {ComplaintStatus.IN_PROGRESS.value},
        "to": ComplaintStatus.RESOLVED.value,
        "requires_assignment": True,
    },
}


async def transition_complaint_status(complaint_id, action: str, actor, notes, db) -> Complaint:
    """
    Drives the status state machine off the TRANSITIONS table above.
    action is one of "approve", "reject", "start", "resolve". notes
    is the optional transition note for approve/start/resolve, or the
    required rejection reason for reject (stored in
    Complaint.reject_reason too, not just the ComplaintUpdate log).

    Role enforcement (admin-only for approve/reject, staff-or-admin
    for start/resolve) happens at the route layer via require_roles,
    same as every other route in this app. This function only checks
    what a role check alone can't: for start/resolve, that a staff
    caller (not admin, admins bypass this) is the complaint's own
    assigned staff member, not someone else's.

    Does not commit, same convention as create_complaint above.
    """
    rule = TRANSITIONS[action]

    complaint = await db.get(Complaint, complaint_id)
    if complaint is None:
        raise ComplaintNotFoundError("Complaint not found.")

    if complaint.status not in rule["from"]:
        raise InvalidStatusTransitionError(
            f"Cannot {action} a complaint that is currently '{complaint.status}'."
        )

    if rule["requires_assignment"]:
        if complaint.assigned_to is None:
            raise InvalidStatusTransitionError(
                f"Cannot {action} a complaint that hasn't been assigned to a staff member yet."
            )
        if actor.role == ROLE_STAFF and complaint.assigned_to != actor.id:
            raise ComplaintNotAssignedToUserError("This complaint isn't assigned to you.")

    old_status = complaint.status
    complaint.status = rule["to"]

    if action == "reject":
        complaint.reject_reason = notes

    db.add(ComplaintUpdate(
        complaint_id=complaint.id,
        updated_by=actor.id,
        old_status=old_status,
        new_status=complaint.status,
        notes=notes,
    ))

    await db.flush()

    return complaint
