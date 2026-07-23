"""
Auto-flags high-risk complaints (#24), based purely on the existing
priority_score, no schema change. "Flagging" means creating a
Notification (existing table) for every admin, once per complaint, not
a new boolean column. score_complaint() itself stays a pure function
(no side effects), flagging is a separate step callers run after
persisting a new priority_score.
"""

from sqlalchemy import select

from app.model import Complaint, Notification, User
from app.utils.constants import ROLE_ADMIN

# Anything scoring at or above this is considered high-risk. The scale is
# 0-100 (see predict_priority), 75 leaves real headroom above "High"
# severity alone (70-ish per formula.py) so it takes a genuinely urgent
# combination of factors, not just one, to get flagged.
HIGH_RISK_THRESHOLD = 75

HIGH_RISK_NOTIFICATION_TYPE = "high_risk_alert"


async def flag_if_high_risk(complaint: Complaint, db) -> bool:
    """
    If complaint.priority_score is at or above HIGH_RISK_THRESHOLD,
    notifies every admin, unless a high-risk notification already exists
    for this complaint (so a complaint that stays high-risk across
    multiple rescores doesn't get re-flagged every time). Returns
    whether a new flag was created.
    """
    if complaint.priority_score < HIGH_RISK_THRESHOLD:
        return False

    already_flagged = await db.execute(
        select(Notification.id).where(
            Notification.complaint_id == complaint.id,
            Notification.type == HIGH_RISK_NOTIFICATION_TYPE,
        )
    )
    if already_flagged.first() is not None:
        return False

    admins = await db.execute(select(User).where(User.role == ROLE_ADMIN))
    for admin in admins.scalars().all():
        db.add(
            Notification(
                user_id=admin.id,
                complaint_id=complaint.id,
                type=HIGH_RISK_NOTIFICATION_TYPE,
                title="High-risk complaint flagged",
                message=(
                    f"\"{complaint.title}\" scored {complaint.priority_score}/100 "
                    "and needs urgent attention."
                ),
            )
        )

    await db.commit()
    return True
