from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.auth import get_current_user
from ..model import User
from ..schemas.common import SuccessResponse
from ..schemas.notification import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationOut,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    UnreadCountResponse,
)
from ..services.notification_service import (
    count_unread_notifications,
    delete_notification,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    update_notification_preferences,
)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=SuccessResponse[NotificationListResponse],
    summary="Get all notifications for the logged-in user",
)
async def list_notifications_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifications = await list_notifications(current_user.id, db)
    return SuccessResponse[NotificationListResponse](
        message="Notifications retrieved.",
        data=NotificationListResponse(
            notifications=[NotificationOut.model_validate(n) for n in notifications]
        ),
    )


@router.get(
    "/unread-count",
    response_model=SuccessResponse[UnreadCountResponse],
    summary="Get count of unread notifications",
)
async def unread_count_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await count_unread_notifications(current_user.id, db)
    return SuccessResponse[UnreadCountResponse](
        message="Unread count retrieved.",
        data=UnreadCountResponse(unread_count=count),
    )


@router.patch(
    "/read-all",
    response_model=SuccessResponse[MarkAllReadResponse],
    summary="Mark all notifications as read",
)
async def mark_all_read_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    marked = await mark_all_notifications_read(current_user.id, db)
    await db.commit()
    return SuccessResponse[MarkAllReadResponse](
        message="All notifications marked as read.",
        data=MarkAllReadResponse(marked_read=marked),
    )


@router.patch(
    "/{notification_id}/read",
    response_model=SuccessResponse[NotificationOut],
    summary="Mark one notification as read",
)
async def mark_read_route(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Raises:
        NotificationNotFoundError: 404, if the notification doesn't
            exist or doesn't belong to the caller.
    """
    notification = await mark_notification_read(notification_id, current_user.id, db)
    await db.commit()
    return SuccessResponse[NotificationOut](
        message="Notification marked as read.",
        data=NotificationOut.model_validate(notification),
    )


@router.delete(
    "/{notification_id}",
    response_model=SuccessResponse[None],
    summary="Delete a specific notification",
)
async def delete_notification_route(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Raises:
        NotificationNotFoundError: 404, if the notification doesn't
            exist or doesn't belong to the caller.
    """
    await delete_notification(notification_id, current_user.id, db)
    await db.commit()
    return SuccessResponse[None](message="Notification deleted.")


@router.post(
    "/preferences",
    response_model=SuccessResponse[NotificationPreferencesResponse],
    summary="Update notification preferences (email)",
)
async def update_preferences_route(
    body: NotificationPreferencesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await update_notification_preferences(current_user.id, body.email_enabled, db)
    await db.commit()
    return SuccessResponse[NotificationPreferencesResponse](
        message="Preferences updated.",
        data=NotificationPreferencesResponse(email_enabled=user.notification_email_enabled),
    )
