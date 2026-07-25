"""Sends transactional email (verification, password reset) via SMTP when
configured; otherwise logs the message -- link included -- to the console.
Mirrors ai_service.py's real-call-vs-canned-fallback pattern for
OPENAI_API_KEY: the feature works end-to-end in local dev with no mail
server, and starts actually delivering once SMTP_HOST is set.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("lism.email")


def send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        # No logging.basicConfig is set up anywhere in this app, so the root
        # logger defaults to WARNING -- an INFO call here would silently
        # vanish instead of being usable as the fallback delivery channel.
        logger.warning("EMAIL not sent (no SMTP_HOST configured) -- logging instead:\nTo: %s\nSubject: %s\n\n%s", to_email, subject, body)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(message)


def send_verification_email(to_email: str, name: str, verify_url: str) -> None:
    send_email(
        to_email,
        subject="Verify your LISM AI Classroom email",
        body=(
            f"Hi {name},\n\n"
            "Please confirm your email address for LISM AI Classroom by opening this link:\n"
            f"{verify_url}\n\n"
            "If you didn't create this account, you can ignore this email."
        ),
    )


def send_password_reset_email(to_email: str, name: str, reset_url: str) -> None:
    send_email(
        to_email,
        subject="Reset your LISM AI Classroom password",
        body=(
            f"Hi {name},\n\n"
            "Someone requested a password reset for this account. Open this link to choose a new password "
            "(it expires in 1 hour):\n"
            f"{reset_url}\n\n"
            "If you didn't request this, you can ignore this email -- your password won't change."
        ),
    )
