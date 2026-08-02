"""
Notification CRUD (section 6 of the API design doc), plus the
create_notification helper complaint_service.py calls at each of the
six trigger points the doc lists: approval, rejection, assignment,
progress update, resolution, and closure.
"""

from sqlalchemy import func as sa_func
from sqlalchemy import select, update

from app.model import Notification, User
from app.utils.exceptions import NotificationNotFoundError


async def create_notification(user_id, complaint_id, type_: str, title: str, message: str, db) -> Notification:
    """
    Shared by every trigger point in complaint_service.py. Does not
    commit, same convention as create_complaint and friends, callers
    are already mid-transaction for the complaint mutation this
    notification is about.
    """
    notification = Notification(
        user_id=user_id,
        complaint_id=complaint_id,
        type=type_,
        title=title,
        message=message,
    )
    db.add(notification)
    await db.flush()
    return notification


async def list_notifications(user_id, db) -> list[Notification]:
    """Every notification for a user, newest first, backing GET /notifications."""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
    )
    return result.scalars().all()


async def count_unread_notifications(user_id, db) -> int:
    """Backs GET /notifications/unread-count."""
    result = await db.execute(
        select(sa_func.count()).where(
            Notification.user_id == user_id, Notification.is_read.is_(False)
        )
    )
    return result.scalar_one()


async def _get_own_notification(notification_id, user_id, db) -> Notification:
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        raise NotificationNotFoundError("Notification not found.")
    return notification


async def mark_notification_read(notification_id, user_id, db) -> Notification:
    """
    Backs PATCH /notifications/{id}/read. A notification belonging to
    someone else is reported as 404, not 403, same reasoning as
    NotificationNotFoundError's own docstring: this endpoint shouldn't
    let a caller confirm another user's notification IDs exist.

    Does not commit, same convention as create_notification above.
    """
    notification = await _get_own_notification(notification_id, user_id, db)
    notification.is_read = True
    await db.flush()
    return notification


async def mark_all_notifications_read(user_id, db) -> int:
    """
    Backs PATCH /notifications/read-all. Returns how many rows were
    actually flipped from unread, so the route can report a count.

    Does not commit, same convention as create_notification above.
    """
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.flush()
    return result.rowcount


async def delete_notification(notification_id, user_id, db) -> None:
    """
    Backs DELETE /notifications/{id}. Does not commit, same
    convention as create_notification above.
    """
    notification = await _get_own_notification(notification_id, user_id, db)
    await db.delete(notification)
    await db.flush()


async def update_notification_preferences(user_id, email_enabled: bool, db) -> User:
    """
    Backs POST /notifications/preferences. In-app notifications
    (the Notification table) are never optional, this only toggles
    whether the app should additionally email the user, an app-level
    concern that lives on User rather than on the Notification model
    itself, there's nothing per-notification about it.

    Does not commit, same convention as create_notification above.
    """
    user = await db.get(User, user_id)
    user.notification_email_enabled = email_enabled
    await db.flush()
    return user
