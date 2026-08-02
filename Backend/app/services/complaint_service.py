"""
Complaint submission (#41), assignment, internal notes, and the
status state machine.

Creates a real Complaint row from a citizen's POST /complaints request,
then immediately runs it through the same ML pipeline the /ml/* routes
already expose individually (priority scoring, department routing,
high-risk flagging), so a freshly filed complaint doesn't sit with a
meaningless priority_score=0/no department until someone separately
calls those endpoints. Reuses those exact services rather than
duplicating any scoring/routing logic here.
"""

import shutil
from pathlib import Path

from sqlalchemy import func as sa_func
from sqlalchemy import select, update

from app.core.config import settings
from app.model import ChatSession, Complaint, ComplaintImage, ComplaintUpdate, User
from app.schemas.complaint import ComplaintAssignRequest, ComplaintCreate, ComplaintStatus
from app.services.notification_service import create_notification
from app.services.priority_service import score_complaint
from app.services.risk_alert_service import flag_if_high_risk
from app.services.routing_service import route_complaint
from app.utils.constants import ROLE_CITIZEN, ROLE_STAFF
from app.utils.exceptions import (
    ComplaintNotAssignableError,
    ComplaintNotAssignedToUserError,
    ComplaintNotFoundError,
    ComplaintNotOwnerError,
    InvalidStaffAssignmentError,
    InvalidStatusTransitionError,
    TooManyAttachmentsError,
)
from app.utils.storage import save_attachment_file, validate_upload

# Only these two columns are meaningful to sort a complaint list by,
# whatever GET /complaints?sort_by= is given, the route validates it
# against this same set before calling list_complaints.
SORT_COLUMNS = {
    "created_at": Complaint.created_at,
    "priority_score": Complaint.priority_score,
}

# A complaint already in one of these has nothing left to assign, work
# on it is either done or it was never going to be actioned.
NOT_ASSIGNABLE_STATUSES = {
    ComplaintStatus.RESOLVED.value,
    ComplaintStatus.CLOSED.value,
    ComplaintStatus.REJECTED.value,
    ComplaintStatus.WITHDRAWN.value,
}


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
        latitude=data.location.latitude,
        longitude=data.location.longitude,
        ward_code=data.ward_code,
    )
    db.add(complaint)
    await db.flush()

    complaint.priority_score = round(await score_complaint(complaint, db))

    department = await route_complaint(complaint, db)
    complaint.department_id = department.id if department else None

    await flag_if_high_risk(complaint, db)

    return complaint


async def list_my_complaints(citizen_id, db) -> list[Complaint]:
    """Every complaint a citizen has filed, newest first."""
    result = await db.execute(
        select(Complaint)
        .where(Complaint.citizen_id == citizen_id)
        .order_by(Complaint.created_at.desc())
    )
    return result.scalars().all()


async def list_complaints(
    current_user,
    db,
    status: str | None = None,
    category: str | None = None,
    ward_code: str | None = None,
    assigned_to=None,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "created_at",
    order: str = "desc",
) -> tuple[list[Complaint], int]:
    """
    Role-filtered, paginated complaint list backing GET /complaints.

    Citizens only ever see their own complaints, the same privacy
    boundary GET /complaints/mine already enforces, no filter can be
    used to see someone else's. Staff and admin see every complaint,
    narrowed by whatever filters are passed, matching the API design
    doc's "Roles: All" for this endpoint.

    Returns (complaints, total) — total is the full matching count
    before pagination is applied, so the route can build meta.total
    and meta.total_pages.
    """
    query = select(Complaint)

    if current_user.role == ROLE_CITIZEN:
        query = query.where(Complaint.citizen_id == current_user.id)

    if status is not None:
        query = query.where(Complaint.status == status)
    if category is not None:
        query = query.where(Complaint.category == category)
    if ward_code is not None:
        query = query.where(Complaint.ward_code == ward_code)
    if assigned_to is not None:
        query = query.where(Complaint.assigned_to == assigned_to)

    count_result = await db.execute(select(sa_func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    sort_column = SORT_COLUMNS.get(sort_by, Complaint.created_at)
    query = query.order_by(sort_column.desc() if order == "desc" else sort_column.asc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    complaints = result.scalars().all()

    return complaints, total


async def list_complaints_by_ward(ward_code: str, db) -> list[Complaint]:
    """
    Every complaint in a given ward, newest first, backing GET
    /complaints/ward/{ward_id}. Officer/admin-only per the design doc
    (unlike GET /complaints' own ward_code filter, which citizens can
    also use, scoped to their own complaints), so there's no ownership
    boundary to enforce here, staff and admin already see every
    complaint regardless of ward.
    """
    result = await db.execute(
        select(Complaint)
        .where(Complaint.ward_code == ward_code)
        .order_by(Complaint.created_at.desc())
    )
    return result.scalars().all()


async def list_complaints_by_category(category: str, db) -> list[Complaint]:
    """
    Every complaint in a given category, newest first, backing GET
    /complaints/category/{category}. Same officer/admin-only reasoning
    as list_complaints_by_ward above.
    """
    result = await db.execute(
        select(Complaint)
        .where(Complaint.category == category)
        .order_by(Complaint.created_at.desc())
    )
    return result.scalars().all()


async def get_complaint_history(complaint_id, current_user, db) -> list[tuple[ComplaintUpdate, User]]:
    """
    Only the status-change rows on a complaint's timeline, oldest
    first, each paired with who made the change. Backs GET
    /complaints/{id}/history, distinct from GET /complaints/{id}/updates
    (list_complaint_notes above), which returns internal notes
    instead, a ComplaintUpdate row here counts as "history" only when
    it actually carries a status change (new_status IS NOT NULL), the
    opposite filter from list_complaint_notes.

    Same ownership boundary as get_complaint_detail: a citizen can
    only see their own complaint's history, staff and admin can see
    any.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        ComplaintNotOwnerError: 403, if a citizen requests a complaint
            that isn't theirs.
    """
    await _get_visible_complaint(complaint_id, current_user, db)

    result = await db.execute(
        select(ComplaintUpdate)
        .where(ComplaintUpdate.complaint_id == complaint_id, ComplaintUpdate.new_status.isnot(None))
        .order_by(ComplaintUpdate.created_at)
    )
    changes = result.scalars().all()

    changer_ids = {change.updated_by for change in changes}
    changers_by_id = {}
    if changer_ids:
        result = await db.execute(select(User).where(User.id.in_(changer_ids)))
        changers_by_id = {user.id: user for user in result.scalars().all()}

    return [(change, changers_by_id.get(change.updated_by)) for change in changes]


async def _get_visible_complaint(complaint_id, current_user, db) -> Complaint:
    """
    Fetches a complaint and enforces the citizen-ownership boundary
    shared by every route that reads a single complaint by id (detail,
    attachments, and any future one like it). Staff and admin can view
    any complaint.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        ComplaintNotOwnerError: 403, if a citizen requests a complaint
            that isn't theirs.
    """
    complaint = await db.get(Complaint, complaint_id)
    if complaint is None:
        raise ComplaintNotFoundError("Complaint not found.")

    if current_user.role == ROLE_CITIZEN and complaint.citizen_id != current_user.id:
        raise ComplaintNotOwnerError("You can only view your own complaints.")

    return complaint


async def get_complaint_detail(complaint_id, current_user, db) -> tuple[Complaint, User | None]:
    """
    Fetches a single complaint plus its assigned staff member (if
    any), backing GET /complaints/{id}. Returns (complaint, staff),
    same shape as assign_complaint above, so the route can build
    StaffSummary/department names without a second round trip.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        ComplaintNotOwnerError: 403, if a citizen requests a complaint
            that isn't theirs.
    """
    complaint = await _get_visible_complaint(complaint_id, current_user, db)

    staff = None
    if complaint.assigned_to:
        staff = await db.get(User, complaint.assigned_to)

    return complaint, staff


async def edit_complaint(complaint_id, current_user, title, description, db) -> Complaint:
    """
    Edits a complaint's title/description, backing PATCH
    /complaints/{id}. Enforced as citizen-and-owner-only, by
    require_roles(ROLE_CITIZEN) at the route level plus the ownership
    check below, unlike most routes in this module staff and admin do
    NOT get a bypass here, per the design doc this is citizen-only.
    Only while the complaint is still "submitted", the closest
    equivalent this app's real state machine has to the doc's "draft"
    state, once an officer has approved it the content is no longer
    the citizen's alone to change.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        ComplaintNotOwnerError: 403, if the complaint isn't the
            caller's own.
        InvalidStatusTransitionError: 409, if the complaint isn't
            currently "submitted".

    Locks the complaint row (SELECT ... FOR UPDATE) before checking
    its status, same reasoning as transition_complaint_status: without
    it, this edit could race a concurrent approve on the same
    complaint, both reading "submitted" and proceeding.

    Does not commit, same convention as create_complaint above.
    """
    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id).with_for_update()
    )
    complaint = result.scalar_one_or_none()
    if complaint is None:
        raise ComplaintNotFoundError("Complaint not found.")

    if complaint.citizen_id != current_user.id:
        raise ComplaintNotOwnerError("You can only edit your own complaints.")

    if complaint.status != ComplaintStatus.SUBMITTED.value:
        raise InvalidStatusTransitionError(
            f"Cannot edit a complaint that is currently '{complaint.status}', "
            f"only complaints still awaiting approval can be edited."
        )

    if title is not None:
        complaint.title = title
    if description is not None:
        complaint.description = description

    await db.flush()
    return complaint


async def delete_complaint(complaint_id, db) -> None:
    """
    Hard-deletes a complaint, backing DELETE /complaints/{id}.
    Admin-only, enforced by require_roles(ROLE_ADMIN) at the route
    level, no ownership concept applies here.

    ComplaintUpdate, ComplaintImage, and Rating rows all cascade-delete
    at the database level (ondelete="CASCADE" on their foreign keys),
    and Notification.complaint_id is set null there too, none of those
    need handling here. ChatSession.complaint_id has no ondelete
    configured though, deleting a complaint a chatbot conversation
    filed would otherwise hit a real foreign key violation, nulled out
    explicitly first (preserving the conversation itself, just
    detaching the link) to avoid that.

    Also best-effort removes the complaint's uploaded attachment files
    from disk (see app/utils/storage.py). The DB rows are gone via
    cascade regardless, but the files aren't tracked by any foreign
    key and would otherwise be orphaned.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.

    Does not commit, same convention as create_complaint above.
    """
    complaint = await db.get(Complaint, complaint_id)
    if complaint is None:
        raise ComplaintNotFoundError("Complaint not found.")

    await db.execute(
        update(ChatSession)
        .where(ChatSession.complaint_id == complaint_id)
        .values(complaint_id=None)
    )

    attachment_dir = Path(settings.UPLOAD_DIR) / "complaints" / str(complaint_id)
    shutil.rmtree(attachment_dir, ignore_errors=True)

    await db.delete(complaint)
    await db.flush()


async def list_complaint_attachments(complaint_id, current_user, db) -> list[ComplaintImage]:
    """
    Every attachment on a complaint, oldest first, backing
    GET /complaints/{id}/attachments. Same visibility boundary as
    get_complaint_detail: a citizen can only list their own
    complaint's attachments, staff and admin can list any.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        ComplaintNotOwnerError: 403, if a citizen requests a complaint
            that isn't theirs.
    """
    await _get_visible_complaint(complaint_id, current_user, db)

    result = await db.execute(
        select(ComplaintImage)
        .where(ComplaintImage.complaint_id == complaint_id)
        .order_by(ComplaintImage.created_at)
    )
    return result.scalars().all()


async def upload_complaint_attachment(
    complaint_id,
    current_user,
    content_type: str,
    file_bytes: bytes,
    db,
) -> ComplaintImage:
    """
    Validates and stores a new attachment on a complaint, backing
    POST /complaints/{id}/attachments. Same visibility boundary as
    list_complaint_attachments: a citizen can only upload to their
    own complaint, staff and admin can upload to any. The design doc
    lists this route's roles as "Citizen, Officer" only, extended
    here to include admin too, matching every other route in this
    module where admin has a superset of staff's access.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        ComplaintNotOwnerError: 403, if a citizen requests a complaint
            that isn't theirs.
        UnsupportedFileTypeError: 415 (FILE_002), if content_type
            isn't JPG/PNG/PDF/DOC/DOCX, or file_bytes' actual leading
            bytes don't match what real files of that type start with.
        FileTooLargeError: 413 (FILE_001), if the file exceeds
            settings.MAX_UPLOAD_SIZE_BYTES.
        TooManyAttachmentsError: 409 (FILE_003), if the complaint
            already has settings.MAX_ATTACHMENTS_PER_COMPLAINT
            attachments.

    Does not commit, same convention as create_complaint above.
    """
    await _get_visible_complaint(complaint_id, current_user, db)

    validate_upload(content_type, file_bytes)

    count_result = await db.execute(
        select(sa_func.count())
        .select_from(ComplaintImage)
        .where(ComplaintImage.complaint_id == complaint_id)
    )
    if count_result.scalar_one() >= settings.MAX_ATTACHMENTS_PER_COMPLAINT:
        raise TooManyAttachmentsError(
            f"This complaint already has the maximum of "
            f"{settings.MAX_ATTACHMENTS_PER_COMPLAINT} attachments."
        )

    image_url = save_attachment_file(complaint_id, content_type, file_bytes)

    attachment = ComplaintImage(complaint_id=complaint_id, image_url=image_url)
    db.add(attachment)
    await db.flush()

    return attachment


async def assign_complaint(
    complaint_id,
    admin_id,
    data: ComplaintAssignRequest,
    db,
) -> tuple[Complaint, User]:
    """
    Assigns a complaint to a staff member. Only sets assigned_to,
    deliberately does NOT change complaint.status.

    Originally this also jumped status straight to "in_progress" on
    assignment, but that collides with the actual status state
    machine (approve/start/resolve/reject, see
    transition_complaint_status below): "who is responsible" and
    "what stage the complaint is at" are orthogonal concerns, same as
    in any real ticketing system, an admin can reassign a complaint
    that's still just "approved," or even one that's "in_progress"
    already, without that alone meaning work started or restarted.
    The actual in_progress transition is now owned by /start, which
    also requires the complaint to already be assigned before it can
    be started.

    Logs the assignment as a ComplaintUpdate row rather than as extra
    columns on Complaint itself (see complaint_assign_schema.py's own
    note on this) — old_status/new_status stay null here, same as an
    internal note, since assigning doesn't change status.

    Returns (complaint, staff) rather than just the complaint, since
    the route needs the staff user to build StaffSummary (which needs
    a Department join complaint_service has no reason to know about),
    and re-fetching the staff row a second time in the route would be
    redundant.

    Locks the complaint row (SELECT ... FOR UPDATE) before checking
    its status, so a concurrent assign and a concurrent status
    transition on the same complaint can't both read a stale status
    and both go through, the second waits for the first's transaction
    to commit and then sees the up-to-date row.

    Does not commit, same convention as create_complaint above.
    """
    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id).with_for_update()
    )
    complaint = result.scalar_one_or_none()
    if complaint is None:
        raise ComplaintNotFoundError("Complaint not found.")

    if complaint.status in NOT_ASSIGNABLE_STATUSES:
        raise ComplaintNotAssignableError(
            f"Complaint is already {complaint.status} and can no longer be assigned."
        )

    staff = await db.get(User, data.assigned_to)
    if staff is None or staff.role != ROLE_STAFF:
        raise InvalidStaffAssignmentError(
            "assigned_to must be an existing user with role 'staff'."
        )

    complaint.assigned_to = staff.id

    db.add(ComplaintUpdate(
        complaint_id=complaint.id,
        updated_by=admin_id,
        old_status=None,
        new_status=None,
        notes=data.notes,
    ))

    await create_notification(
        staff.id,
        complaint.id,
        "complaint_assigned",
        "New complaint assigned to you",
        f'You have been assigned complaint "{complaint.title}".',
        db,
    )

    await db.flush()

    return complaint, staff


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

# Notification copy for each TRANSITIONS action, keyed the same way.
# "start" is the closest real equivalent this app's state machine has
# to the design doc's "progress update" trigger (see complaint_service
# module docstring reasoning: internal notes are deliberately never
# citizen-visible, so add_complaint_note can't be the trigger for that
# one instead).
TRANSITION_NOTIFICATIONS = {
    "approve": ("complaint_approved", "Complaint approved", "has been approved and is awaiting work to begin"),
    "reject": ("complaint_rejected", "Complaint rejected", "was rejected"),
    "start": ("complaint_in_progress", "Work started on your complaint", "is now being worked on"),
    "resolve": ("complaint_resolved", "Complaint resolved", "has been marked resolved"),
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

    Locks the complaint row (SELECT ... FOR UPDATE) before checking
    its status, so two concurrent transition requests on the same
    complaint can't both read the same pre-transition status and both
    succeed, the second waits for the first's transaction to commit
    and then sees the already-updated status.

    Does not commit, same convention as create_complaint above.
    """
    rule = TRANSITIONS[action]

    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id).with_for_update()
    )
    complaint = result.scalar_one_or_none()
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
        complaint.assigned_to = None

    db.add(ComplaintUpdate(
        complaint_id=complaint.id,
        updated_by=actor.id,
        old_status=old_status,
        new_status=complaint.status,
        notes=notes,
    ))

    type_, title, message_suffix = TRANSITION_NOTIFICATIONS[action]
    await create_notification(
        complaint.citizen_id,
        complaint.id,
        type_,
        title,
        f'Your complaint "{complaint.title}" {message_suffix}.',
        db,
    )

    await db.flush()

    return complaint


# submitted --withdraw--> withdrawn
# resolved  --close-----> closed
#
# Citizen-initiated transitions, deliberately kept separate from
# TRANSITIONS/transition_complaint_status above rather than folded
# into that table: those are all staff/admin role-gated (enforced via
# require_roles at the route layer), these two are ownership-gated
# instead, a genuinely different authorization shape, "is this caller
# an admin/the assignee" vs. "is this caller the citizen who filed
# it." The design doc also lists "System" as an actor for close (an
# automatic 7-day timeout), that's a scheduled job, out of scope here,
# this only covers the citizen-confirms path.
OWNER_TRANSITIONS = {
    "withdraw": {
        "from": {ComplaintStatus.SUBMITTED.value},
        "to": ComplaintStatus.WITHDRAWN.value,
    },
    "close": {
        "from": {ComplaintStatus.RESOLVED.value},
        "to": ComplaintStatus.CLOSED.value,
    },
}


async def transition_complaint_status_as_owner(complaint_id, action: str, citizen, db) -> Complaint:
    """
    Drives OWNER_TRANSITIONS above. action is "withdraw" or "close".
    Role enforcement (citizen-only) happens at the route layer via
    require_roles, same as transition_complaint_status. This function
    checks what a role check alone can't: that the caller is this
    specific complaint's own citizen, not just some citizen.

    Locks the complaint row (SELECT ... FOR UPDATE) before checking
    its status, same reasoning as transition_complaint_status above.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
        ComplaintNotOwnerError: 403, if the complaint isn't the
            caller's own.
        InvalidStatusTransitionError: 409, if the complaint isn't
            currently in the right state for this action.

    Does not commit, same convention as create_complaint above.
    """
    rule = OWNER_TRANSITIONS[action]

    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id).with_for_update()
    )
    complaint = result.scalar_one_or_none()
    if complaint is None:
        raise ComplaintNotFoundError("Complaint not found.")

    if complaint.citizen_id != citizen.id:
        raise ComplaintNotOwnerError(f"You can only {action} your own complaints.")

    if complaint.status not in rule["from"]:
        raise InvalidStatusTransitionError(
            f"Cannot {action} a complaint that is currently '{complaint.status}'."
        )

    old_status = complaint.status
    complaint.status = rule["to"]

    db.add(ComplaintUpdate(
        complaint_id=complaint.id,
        updated_by=citizen.id,
        old_status=old_status,
        new_status=complaint.status,
        notes=None,
    ))

    if action == "close" and complaint.assigned_to is not None:
        # The citizen already knows they just confirmed the closure
        # themselves, notifying them about their own action wouldn't
        # add anything, but the assigned staff member finding out the
        # case is now closed is genuinely new information for them.
        await create_notification(
            complaint.assigned_to,
            complaint.id,
            "complaint_closed",
            "Complaint closed",
            f'The citizen has confirmed and closed complaint "{complaint.title}".',
            db,
        )

    await db.flush()

    return complaint
