"""
Pytest suite for the Notification API's service layer (list, mark
read, mark all read, delete, unread count, preferences), plus the
create_notification trigger points wired into complaint_service.py's
transitions (approve/reject/start/resolve, assign, close).

Hits real Supabase, same reasoning as the other unmocked service
suites in this project.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.model import Complaint, ComplaintUpdate, Notification, User
from app.schemas.complaint import ComplaintAssignRequest, ComplaintCreate, ComplaintLocation
from app.services.complaint_service import (
    assign_complaint,
    create_complaint,
    transition_complaint_status,
    transition_complaint_status_as_owner,
)
from app.services.notification_service import (
    count_unread_notifications,
    delete_notification,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    update_notification_preferences,
)
from app.utils.exceptions import NotificationNotFoundError


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def citizen(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Notif Citizen",
        email=f"pytest-notif-{uuid.uuid4()}@example.com",
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
        name="Pytest Notif Admin",
        email=f"pytest-notif-admin-{uuid.uuid4()}@example.com",
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
        name="Pytest Notif Staff",
        email=f"pytest-notif-staff-{uuid.uuid4()}@example.com",
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
    result = await db.execute(select(Notification).where(Notification.complaint_id == complaint.id))
    for n in result.scalars().all():
        await db.delete(n)
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


class TestTransitionNotifications:
    async def test_approve_notifies_the_citizen(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        notifications = await list_notifications(citizen.id, db)
        matching = [n for n in notifications if n.complaint_id == complaint.id]

        assert len(matching) == 1
        assert matching[0].type == "complaint_approved"
        assert matching[0].is_read is False

        await _cleanup(db, complaint)

    async def test_reject_notifies_the_citizen(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "reject", admin, "not a real issue", db)
        await db.commit()

        notifications = await list_notifications(citizen.id, db)
        matching = [n for n in notifications if n.complaint_id == complaint.id]

        assert len(matching) == 1
        assert matching[0].type == "complaint_rejected"

        await _cleanup(db, complaint)

    async def test_assign_notifies_the_staff_member(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        await assign_complaint(complaint.id, admin.id, ComplaintAssignRequest(assigned_to=staff.id), db)
        await db.commit()

        notifications = await list_notifications(staff.id, db)
        matching = [n for n in notifications if n.complaint_id == complaint.id]

        assert len(matching) == 1
        assert matching[0].type == "complaint_assigned"

        await _cleanup(db, complaint)

    async def test_resolve_notifies_the_citizen(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        await assign_complaint(complaint.id, admin.id, ComplaintAssignRequest(assigned_to=staff.id), db)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await transition_complaint_status(complaint.id, "start", staff, None, db)
        await transition_complaint_status(complaint.id, "resolve", staff, None, db)
        await db.commit()

        notifications = await list_notifications(citizen.id, db)
        types = {n.type for n in notifications if n.complaint_id == complaint.id}

        assert "complaint_resolved" in types

        await _cleanup(db, complaint)

    async def test_close_notifies_the_assigned_staff_member(self, db, citizen, admin, staff):
        complaint = await _make_complaint(db, citizen)
        await assign_complaint(complaint.id, admin.id, ComplaintAssignRequest(assigned_to=staff.id), db)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await transition_complaint_status(complaint.id, "start", staff, None, db)
        await transition_complaint_status(complaint.id, "resolve", staff, None, db)
        await transition_complaint_status_as_owner(complaint.id, "close", citizen, db)
        await db.commit()

        notifications = await list_notifications(staff.id, db)
        matching = [n for n in notifications if n.complaint_id == complaint.id and n.type == "complaint_closed"]

        assert len(matching) == 1

        await _cleanup(db, complaint)

    async def test_withdraw_creates_no_notification(self, db, citizen):
        # withdraw isn't in the design doc's notification-trigger list,
        # unlike close it shouldn't create anything, this also proves
        # transition_complaint_status_as_owner's close-only guard
        # doesn't accidentally fire for withdraw too.
        complaint = await _make_complaint(db, citizen)

        await transition_complaint_status_as_owner(complaint.id, "withdraw", citizen, db)
        await db.commit()

        notifications = await list_notifications(citizen.id, db)
        assert not any(n.complaint_id == complaint.id for n in notifications)

        await _cleanup(db, complaint)


class TestListNotifications:
    async def test_returns_only_the_users_own_notifications(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        mine = await list_notifications(citizen.id, db)
        admins = await list_notifications(admin.id, db)

        # The complaint may also independently score high-risk (real
        # LLM severity extraction, flag_if_high_risk notifies every
        # admin regardless of who approved it), so admin isn't
        # guaranteed zero notifications for this complaint, only zero
        # of the citizen-scoped "complaint_approved" kind.
        assert any(n.type == "complaint_approved" for n in mine)
        assert not any(n.type == "complaint_approved" and n.complaint_id == complaint.id for n in admins)

        await _cleanup(db, complaint)

    async def test_empty_for_a_user_with_no_notifications(self, db, citizen):
        notifications = await list_notifications(citizen.id, db)
        assert notifications == []


class TestUnreadCount:
    async def test_counts_only_unread(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        before = await count_unread_notifications(citizen.id, db)
        assert before >= 1

        notifications = await list_notifications(citizen.id, db)
        target = next(n for n in notifications if n.complaint_id == complaint.id)
        await mark_notification_read(target.id, citizen.id, db)
        await db.commit()

        after = await count_unread_notifications(citizen.id, db)
        assert after == before - 1

        await _cleanup(db, complaint)


class TestMarkNotificationRead:
    async def test_marks_a_notification_read(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        notifications = await list_notifications(citizen.id, db)
        target = next(n for n in notifications if n.complaint_id == complaint.id)
        assert target.is_read is False

        updated = await mark_notification_read(target.id, citizen.id, db)
        await db.commit()

        assert updated.is_read is True

        await _cleanup(db, complaint)

    async def test_cannot_mark_someone_elses_notification_read(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        notifications = await list_notifications(citizen.id, db)
        target = next(n for n in notifications if n.complaint_id == complaint.id)

        with pytest.raises(NotificationNotFoundError):
            await mark_notification_read(target.id, admin.id, db)

        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_notification(self, db, citizen):
        with pytest.raises(NotificationNotFoundError):
            await mark_notification_read(uuid.uuid4(), citizen.id, db)


class TestMarkAllNotificationsRead:
    async def test_marks_every_unread_notification(self, db, citizen, admin):
        first = await _make_complaint(db, citizen)
        second = await _make_complaint(db, citizen)
        await transition_complaint_status(first.id, "approve", admin, None, db)
        await transition_complaint_status(second.id, "approve", admin, None, db)
        await db.commit()

        marked = await mark_all_notifications_read(citizen.id, db)
        await db.commit()

        assert marked >= 2
        assert await count_unread_notifications(citizen.id, db) == 0

        await _cleanup(db, first)
        await _cleanup(db, second)

    async def test_zero_when_nothing_to_mark(self, db, citizen):
        marked = await mark_all_notifications_read(citizen.id, db)
        assert marked == 0


class TestDeleteNotification:
    async def test_deletes_own_notification(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        notifications = await list_notifications(citizen.id, db)
        target = next(n for n in notifications if n.complaint_id == complaint.id)

        await delete_notification(target.id, citizen.id, db)
        await db.commit()

        assert await db.get(Notification, target.id) is None

        await db.delete(complaint)
        await db.commit()

    async def test_cannot_delete_someone_elses_notification(self, db, citizen, admin):
        complaint = await _make_complaint(db, citizen)
        await transition_complaint_status(complaint.id, "approve", admin, None, db)
        await db.commit()

        notifications = await list_notifications(citizen.id, db)
        target = next(n for n in notifications if n.complaint_id == complaint.id)

        with pytest.raises(NotificationNotFoundError):
            await delete_notification(target.id, admin.id, db)

        await _cleanup(db, complaint)

    async def test_rejects_a_nonexistent_notification(self, db, citizen):
        with pytest.raises(NotificationNotFoundError):
            await delete_notification(uuid.uuid4(), citizen.id, db)


class TestUpdateNotificationPreferences:
    async def test_updates_the_email_flag(self, db, citizen):
        assert citizen.notification_email_enabled is True

        updated = await update_notification_preferences(citizen.id, False, db)
        await db.commit()

        assert updated.notification_email_enabled is False

        await update_notification_preferences(citizen.id, True, db)
        await db.commit()
