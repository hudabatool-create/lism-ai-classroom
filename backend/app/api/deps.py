from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.security import decode_access_token
from app.services.data_store import store


def get_current_teacher(request: Request) -> dict:
    token = request.cookies.get(settings.jwt_cookie_name)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    teacher = store.get_teacher(payload["sub"])
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Teacher not found")
    return teacher
