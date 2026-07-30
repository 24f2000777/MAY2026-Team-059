from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.auth import get_current_user
from ..dependencies.roles import require_roles
from ..model import User
from ..schemas.common import SuccessResponse
from ..schemas.complaint import (
    ComplaintCreate,
    ComplaintNote,
    ComplaintNoteAuthor,
    ComplaintNoteCreateRequest,
    ComplaintNoteListResponse,
    ComplaintResponse,
)
from ..services.complaint_service import add_complaint_note, create_complaint, list_complaint_notes
from ..utils.constants import ROLE_ADMIN, ROLE_STAFF


router = APIRouter(
    prefix="/complaints",
    tags=["Complaints"],
)

@router.get("/whoami")
async def whoami(current_user: User = Depends(get_current_user)):
    return {"id": str(current_user.id), "email": current_user.email}


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_complaint(
    body: ComplaintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Files a new complaint and immediately scores/routes it (priority
    score, department, high-risk flag) using the same ML services the
    /ml/* endpoints expose individually.
    """
    complaint = await create_complaint(current_user.id, body, db)
    await db.commit()
    return SuccessResponse[ComplaintResponse](
        message="Complaint submitted.",
        data=ComplaintResponse.model_validate(complaint),
    )


def _to_complaint_note(update, author) -> ComplaintNote:
    return ComplaintNote(
        id=update.id,
        complaint_id=update.complaint_id,
        note_text=update.notes,
        author=ComplaintNoteAuthor(id=author.id, name=author.name, role=author.role),
        created_at=update.created_at,
    )


@router.post(
    "/{complaint_id}/updates",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[ComplaintNote],
    summary="Add an internal note to a complaint (staff/admin only)",
)
async def add_complaint_note_route(
    complaint_id: UUID,
    body: ComplaintNoteCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_STAFF, ROLE_ADMIN)),
):
    """
    Adds an internal note to a complaint. Staff or admin only, never
    visible to the citizen who filed the complaint.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
    """
    note, author = await add_complaint_note(complaint_id, current_user.id, body.note_text, db)
    await db.commit()

    return SuccessResponse[ComplaintNote](
        message="Note added.",
        data=_to_complaint_note(note, author),
    )


@router.get(
    "/{complaint_id}/updates",
    response_model=SuccessResponse[ComplaintNoteListResponse],
    summary="List internal notes on a complaint (staff/admin only)",
)
async def list_complaint_notes_route(
    complaint_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_STAFF, ROLE_ADMIN)),
):
    """
    Lists every internal note on a complaint, oldest first. Staff or
    admin only, never visible to the citizen who filed the complaint.

    Raises:
        ComplaintNotFoundError: 404, if the complaint doesn't exist.
    """
    notes = await list_complaint_notes(complaint_id, db)

    return SuccessResponse[ComplaintNoteListResponse](
        message="Notes retrieved.",
        data=ComplaintNoteListResponse(
            notes=[_to_complaint_note(note, author) for note, author in notes]
        ),
    )
