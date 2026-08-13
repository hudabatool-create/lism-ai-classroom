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


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Deliver one message. Returns whether it actually went.

    Never raises. A failing mail server must not be able to break signing up
    or resetting a password -- and on the reset endpoint it must not even be
    able to change the *shape* of the response. That endpoint deliberately
    answers identically whether or not an account exists, so it cannot be used
    to discover which teachers are registered. An exception escaping from here
    would have produced a 500 for real accounts and a 200 for made-up ones,
    handing an attacker exactly the difference the design exists to hide.
    """
    if not settings.smtp_host:
        # No logging.basicConfig is set up anywhere in this app, so the root
        # logger defaults to WARNING -- an INFO call here would silently
        # vanish instead of being usable as the fallback delivery channel.
        logger.warning("EMAIL not sent (no SMTP_HOST configured) -- logging instead:\nTo: %s\nSubject: %s\n\n%s", to_email, subject, body)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(body)

    try:
        # Port 465 is implicit TLS, which must be negotiated before anything
        # is sent; 587 starts in the clear and upgrades with STARTTLS. Calling
        # starttls() on a 465 connection fails, and most providers -- Gmail
        # included -- document 465 first, so assuming 587's flow would break
        # against the setting people are most likely to reach for.
        implicit_tls = settings.smtp_port == 465
        encrypted = implicit_tls or settings.smtp_starttls

        # Never put a username and password on an unencrypted connection. If
        # someone switches encryption off to get past a stubborn relay, that
        # must not quietly start broadcasting the mail account's password.
        if settings.smtp_username and not encrypted:
            logger.error(
                "EMAIL NOT SENT: SMTP_USERNAME is set but encryption is off. "
                "Credentials will not be sent in the clear. Use port 465, or "
                "leave SMTP_STARTTLS on."
            )
            return False

        if implicit_tls:
            smtp = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15)
        else:
            smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
        with smtp:
            if not implicit_tls and settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(message)
        logger.info("Sent %r to %s", subject, to_email)
        return True
    except Exception as exc:
        # The message is logged in full so the link is still recoverable from
        # the server logs when delivery is broken -- a teacher locked out
        # before a session can still be helped.
        logger.error(
            "EMAIL FAILED (%s: %s) -- the message was:\nTo: %s\nSubject: %s\n\n%s",
            type(exc).__name__, exc, to_email, subject, body,
        )
        return False


def is_configured() -> bool:
    """Whether email can actually be delivered.

    Reported by /api/health so "did my SMTP settings land?" is one request
    rather than a guess -- the failure mode otherwise is silent, and the way
    you discover it is a teacher unable to get back into their account.
    """
    return bool(settings.smtp_host)


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
