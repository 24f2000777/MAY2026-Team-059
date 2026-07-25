from email.message import EmailMessage
import smtplib
import ssl

from app.core.celery_app import celery_app
from app.core.config import settings

@celery_app.task(name="send_email_task")
def send_email_task(recipient: str, subject: str, body: str) -> None:
    """
    Send an email using SMTP (Synchronous, blocking call).
    Runs in a Celery worker so it doesn't block the FastAPI event loop.
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
        timeout=10,
    ) as smtp:
        smtp.starttls(context=context)

        smtp.login(
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD,
        )

        smtp.send_message(message)
