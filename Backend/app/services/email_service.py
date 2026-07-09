"""
Email Service

Responsible for:

- Sending verification OTP
- Sending password reset OTP

This module should contain ONLY email related logic.
"""

from app.core.config import settings
from app.tasks.email_tasks import send_email_task


def send_verification_email(
    *,
    recipient: str,
    otp: str,
) -> None:
    """
    Send email verification OTP.
    """

    subject = "Verify your NAGRIK AI account"

    body = f"""
Hello,

Welcome to NAGRIK AI.

Your verification OTP is:

{otp}

This OTP is valid for {settings.OTP_EXPIRE_SECONDS // 60} minutes.

If you did not request this email, please ignore it.

Regards,
NAGRIK AI Team
"""

    send_email_task.delay(
        recipient=recipient,
        subject=subject,
        body=body,
    )


def send_password_reset_email(
    *,
    recipient: str,
    otp: str,
) -> None:
    """
    Send password reset OTP.
    """

    subject = "Reset your NAGRIK AI password"

    body = f"""
Hello,

Your password reset OTP is:

{otp}

This OTP is valid for {settings.RESET_PASSWORD_OTP_EXPIRE_SECONDS // 60} minutes.

If you did not request this email, please ignore it.

Regards,
NAGRIK AI Team
"""

    send_email_task.delay(
        recipient=recipient,
        subject=subject,
        body=body,
    )