from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr

from app.api.deps import get_current_teacher
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.services.data_store import LOGIN_LOCKOUT_WINDOW, store

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


def _public(teacher: dict) -> dict:
    return {"id": teacher["id"], "name": teacher["name"], "email": teacher["email"]}


def _set_session_cookie(response: Response, token: str) -> None:
    # httpOnly so an XSS payload can't read the token off document.cookie and
    # exfiltrate it -- the browser attaches it to same-site requests itself.
    response.set_cookie(
        key=settings.jwt_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, response: Response):
    if len(payload.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if store.get_teacher_by_email(payload.email):
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    teacher = store.create_teacher(payload.name, payload.email, hash_password(payload.password))
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
    # to ask the server to send back a Set-Cookie that expires it.
    response.delete_cookie(key=settings.jwt_cookie_name, path="/")
    return {"ok": True}


@router.get("/me", response_model=AuthResponse)
def me(teacher: dict = Depends(get_current_teacher)):
    return AuthResponse(teacher=_public(teacher))
