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

    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # The JWT lives in an httpOnly cookie (never readable by frontend JS) rather
    # than localStorage or a response body. `cookie_secure` must be true for any
    # deployment served over HTTPS -- it's false by default only so local dev
    # over plain http still works (browsers drop `Secure` cookies over http).
    jwt_cookie_name: str = "lism_session"
    cookie_secure: bool = False

    frontend_origin: str = "http://localhost:3000"

    openai_api_key: str | None = None

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


settings = Settings()
settings.jwt_secret = _resolve_jwt_secret(settings.jwt_secret)
