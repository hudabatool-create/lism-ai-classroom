from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.security import create_access_token, hash_password, verify_password
from app.services.data_store import store

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    teacher: dict


def _public(teacher: dict) -> dict:
    return {"id": teacher["id"], "name": teacher["name"], "email": teacher["email"]}


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    if store.get_teacher_by_email(payload.email):
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    teacher = store.create_teacher(payload.name, payload.email, hash_password(payload.password))
    token = create_access_token(teacher["id"], teacher["email"])
    return AuthResponse(token=token, teacher=_public(teacher))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    teacher = store.get_teacher_by_email(payload.email)
    if not teacher or not verify_password(payload.password, teacher["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(teacher["id"], teacher["email"])
    return AuthResponse(token=token, teacher=_public(teacher))
