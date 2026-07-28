import logging
import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("lism.config")

# Any of these being the configured secret means "not really configured" --
# never sign tokens with a value that ships in the repo/source history.
_WEAK_JWT_SECRETS = {
    "dev-secret-change-me",
    "change-me",
    "change-me-to-a-long-random-string",
    "secret",
    "changeme",
    "",
}
_MIN_JWT_SECRET_LENGTH = 16


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "LISM AI Classroom API"

    # Real persistence: defaults to a local SQLite file so the app works with
    # zero setup and survives restarts. Point this at a Postgres URL (e.g. a
    # Supabase connection string) for public deployment -- the store is plain
    # SQLAlchemy, so no code changes are needed, just this one value.
    database_url: str = "sqlite:///./lism.db"

    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # The JWT lives in an httpOnly cookie (never readable by frontend JS) rather
    # than localStorage or a response body. `cookie_secure` must be true for any
    # deployment served over HTTPS -- it's false by default only so local dev
    # over plain http still works (browsers drop `Secure` cookies over http).
    #
    # `cookie_samesite` stays "lax" for local dev, where frontend (:3000) and
    # backend (:8000) are different ports of the same host -- browsers treat
    # that as same-site regardless of port. In production, Vercel and Railway
    # put the frontend and backend on two genuinely different domains, which
    # is cross-site: a "lax" cookie silently never gets attached to those
    # requests. Set COOKIE_SAMESITE=none (together with COOKIE_SECURE=true --
    # browsers reject SameSite=None cookies without Secure) once frontend and
    # backend are deployed to different domains.
    jwt_cookie_name: str = "lism_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # Comma-separated when the app answers on more than one domain -- a custom
    # domain plus the platform's default, say. The FIRST one is canonical: it
    # is what goes into student join links and verification emails, so it must
    # be the address you actually want people to see and bookmark.
    #
    # Every listed origin is allowed through CORS. Getting this wrong is
    # invisible until someone tries to log in: the browser blocks the request
    # before it reaches any route, so the server logs stay clean while the
    # whole app appears broken.
    frontend_origin: str = "http://localhost:3000"

    @property
    def frontend_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def canonical_origin(self) -> str:
        """The address used in links we send to people."""
        origins = self.frontend_origins
        return origins[0] if origins else "http://localhost:3000"

    # Optional: sends real email verification / password reset messages via
    # SMTP. Without smtp_host set, email_service.py logs the message (with
    # its link) to the console instead, so those flows still work end-to-end
    # in local dev without a mail server.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@lism.local"

    # Without a key, activity generation falls back to starter templates: the
    # structure and pedagogy are right but the questions are generic, because
    # a template has no knowledge of the topic.
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    # A full lesson deck is a large HTML file; too low and the response is
    # silently truncated mid-tag into a broken activity.
    openai_max_tokens: int = 16000
    openai_timeout_seconds: int = 120

    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_key: str | None = None


def _resolve_jwt_secret(configured: str | None) -> str:
    if configured and configured.lower() not in _WEAK_JWT_SECRETS and len(configured) >= _MIN_JWT_SECRET_LENGTH:
        return configured
    generated = secrets.token_hex(32)
    logger.warning(
        "JWT_SECRET is missing, too short, or a known placeholder value. Generated a random secret for "
        "this process only -- every session will be invalidated on restart, and tokens signed with a "
        "predictable secret would let anyone forge a login. Set a real JWT_SECRET (32+ random characters) "
        "via environment variable before any real deployment."
    )
    return generated


def _validate_cookie_settings(samesite: str, secure: bool) -> None:
    if samesite.lower() == "none" and not secure:
        logger.warning(
            "COOKIE_SAMESITE=none requires COOKIE_SECURE=true -- browsers silently drop SameSite=None cookies "
            "that aren't also Secure, which would make every login appear to fail with no server-side error. "
            "Set COOKIE_SECURE=true (only safe once the app is served over HTTPS, which Vercel/Railway do by "
            "default)."
        )


settings = Settings()
settings.jwt_secret = _resolve_jwt_secret(settings.jwt_secret)
_validate_cookie_settings(settings.cookie_samesite, settings.cookie_secure)
