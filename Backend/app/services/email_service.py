"""
Email Service

Responsible for:

- Sending verification OTP
- Sending password reset OTP

This module should contain ONLY email related logic.
"""

from email.message import EmailMessage
import smtplib
import ssl

from app.core.config import settings


def _send_email(
    *,
    recipient: str,
    subject: str,
    body: str,
) -> None:
    """
    Send an email using SMTP.
    """

    message = EmailMessage()

    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient
    message["Subject"] = subject

    message.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
    ) as smtp:

        smtp.starttls(context=context)

        smtp.login(
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD,
        )

        smtp.send_message(message)


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

    _send_email(
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

    _send_email(
        recipient=recipient,
        subject=subject,
        body=body,
    )