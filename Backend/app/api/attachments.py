from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.auth import get_current_user
from ..model import User
from ..schemas.common import SuccessResponse
from ..schemas.complaint import AttachmentOut
from ..services.complaint_service import delete_attachment, get_attachment

router = APIRouter(
    prefix="/attachments",
    tags=["Attachments"],
)


@router.get(
    "/{attachment_id}",
    response_model=SuccessResponse[AttachmentOut],
    summary="Get a single attachment (owner citizen, staff, or admin)",
)
async def get_attachment_route(
    attachment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches a single attachment's metadata and URL. A citizen can only
    fetch attachments on their own complaint; staff and admin can
    fetch any. image_url is directly fetchable as-is (local
    filesystem storage in dev), there's no separate signed-URL step
    to perform yet, that's a prod/S3-only concern per the design doc.

    Raises:
        AttachmentNotFoundError: 404, if the attachment doesn't exist.
        ComplaintNotOwnerError: 403, if a citizen requests an
            attachment on a complaint that isn't theirs.
    """
    attachment = await get_attachment(attachment_id, current_user, db)

    return SuccessResponse[AttachmentOut](
        message="Attachment retrieved.",
        data=AttachmentOut.model_validate(attachment),
    )


@router.delete(
    "/{attachment_id}",
    response_model=SuccessResponse[None],
    summary="Delete an attachment (owner citizen or admin only)",
)
async def delete_attachment_route(
    attachment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a single attachment, including its file on disk. Only the
    citizen who owns the parent complaint, or an admin, can call
    this, staff cannot delete attachments (per the design doc, unlike
    list/upload which do allow staff).

    Raises:
        AttachmentNotFoundError: 404, if the attachment doesn't exist.
        ComplaintNotOwnerError: 403, if the caller is neither an
            admin nor the owning citizen.
    """
    await delete_attachment(attachment_id, current_user, db)
    await db.commit()

    return SuccessResponse[None](message="Attachment deleted.")
