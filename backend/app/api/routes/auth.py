from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr

from app.api.deps import get_current_teacher
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.services.data_store import LOGIN_LOCKOUT_WINDOW, store
from app.services.email_service import send_password_reset_email, send_verification_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

MIN_PASSWORD_LENGTH = 8


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    teacher: dict


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


def _public(teacher: dict) -> dict:
    return {
        "id": teacher["id"],
        "name": teacher["name"],
        "email": teacher["email"],
        "email_verified": teacher["email_verified"],
    }


def _send_verification_email(teacher: dict, background: BackgroundTasks) -> None:
    """Queue the verification email rather than waiting for the mail server.

    Sending inline made signing up as slow as the slowest SMTP round trip. A
    room of thirty teachers all signing up in the same two minutes of a PD
    session is exactly when that is least affordable, and a mail server having
    a bad day would have shown up as LISM being broken.
    """
    token = store.create_email_verification_token(teacher["id"])
    verify_url = f"{settings.canonical_origin}/verify-email/{token}"
    background.add_task(send_verification_email, teacher["email"], teacher["name"], verify_url)


def _set_session_cookie(response: Response, token: str) -> None:
    # httpOnly so an XSS payload can't read the token off document.cookie and
    # exfiltrate it -- the browser attaches it to same-site requests itself.
    # samesite/secure come from settings so the exact same code works across
    # local dev (frontend/backend share "localhost", lax is fine) and a real
    # deployment (frontend and backend on different domains -- needs
    # samesite=none + secure=true, see config.py).
    response.set_cookie(
        key=settings.jwt_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, response: Response, background: BackgroundTasks):
    if len(payload.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if store.get_teacher_by_email(payload.email):
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    teacher = store.create_teacher(payload.name, payload.email, hash_password(payload.password))
    _send_verification_email(teacher, background)
    token = create_access_token(teacher["id"], teacher["email"])
    _set_session_cookie(response, token)
    return AuthResponse(teacher=_public(teacher))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response):
    if store.is_login_locked(payload.email):
        minutes = int(LOGIN_LOCKOUT_WINDOW.total_seconds() // 60)
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Try again in a few minutes (lockout window: {minutes} min).",
        )

    teacher = store.get_teacher_by_email(payload.email)
    if not teacher or not verify_password(payload.password, teacher["password_hash"]):
        store.record_login_failure(payload.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    store.clear_login_failures(payload.email)
    token = create_access_token(teacher["id"], teacher["email"])
    _set_session_cookie(response, token)
    return AuthResponse(teacher=_public(teacher))


@router.post("/logout")
def logout(response: Response):
    # The cookie is httpOnly, so the frontend can't clear it itself -- it has
    # to ask the server to send back a Set-Cookie that expires it. Browsers
    # only clear a cookie if these attributes match how it was set.
    response.delete_cookie(
        key=settings.jwt_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    return {"ok": True}


@router.get("/me", response_model=AuthResponse)
def me(teacher: dict = Depends(get_current_teacher)):
    return AuthResponse(teacher=_public(teacher))


@router.get("/verify-email/{token}")
def verify_email(token: str):
    teacher_id = store.consume_email_verification_token(token)
    if teacher_id is None:
        raise HTTPException(status_code=400, detail="This verification link is invalid or has expired")
    return {"ok": True}


@router.post("/resend-verification")
def resend_verification(background: BackgroundTasks, teacher: dict = Depends(get_current_teacher)):
    if teacher["email_verified"]:
        return {"ok": True, "already_verified": True}
    _send_verification_email(teacher, background)
    return {"ok": True, "already_verified": False}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, background: BackgroundTasks):
    # Always return the same response whether or not the account exists --
    # otherwise this endpoint becomes a way to check which emails have
    # accounts here.
    teacher = store.get_teacher_by_email(payload.email)
    if teacher:
        token = store.create_password_reset_token(teacher["id"])
        reset_url = f"{settings.canonical_origin}/reset-password/{token}"
        # Queued, so the response takes the same time whether or not the
        # account exists. Sending inline made a real address measurably
        # slower than an unknown one, which is the same leak the identical
        # response body exists to prevent.
        background.add_task(
            send_password_reset_email, teacher["email"], teacher["name"], reset_url
        )
    return {"ok": True}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    if len(payload.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    teacher_id = store.consume_password_reset_token(payload.token)
    if teacher_id is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")
    store.update_teacher_password(teacher_id, hash_password(payload.password))
    store.clear_login_failures(store.get_teacher(teacher_id)["email"])
    return {"ok": True}
