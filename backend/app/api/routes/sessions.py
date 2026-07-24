import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_current_teacher
from app.core.config import settings
from app.services.data_store import store
from app.services.websocket_manager import manager

router = APIRouter(prefix="/api", tags=["sessions"])


def _join_url(code: str) -> str:
    return f"{settings.frontend_origin}/join/{code}"


# --- Teacher-facing ---------------------------------------------------


@router.post("/activities/{activity_id}/launch")
def launch_session(activity_id: str, teacher: dict = Depends(get_current_teacher)):
    activity = store.get_activity(activity_id)
    if not activity or activity["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Activity not found")
    session = store.create_session(teacher["id"], activity_id)
    return {**session, "join_url": _join_url(session["code"])}


@router.get("/sessions")
def list_sessions(teacher: dict = Depends(get_current_teacher)):
    return store.list_sessions(teacher["id"])


@router.get("/sessions/{session_id}")
def get_session(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session = store.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session": {**session, "join_url": _join_url(session["code"])},
        "activity": store.get_activity(session["activity_id"]),
        "students": store.list_students(session_id),
        "responses": store.list_responses(session_id),
    }


@router.get("/sessions/{session_id}/qrcode.png")
def session_qrcode(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session = store.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    img = qrcode.make(_join_url(session["code"]))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.post("/sessions/{session_id}/end")
def end_session(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session = store.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    return store.end_session(session_id)


# --- Public, student-facing (no login) ---------------------------------------------------


class JoinRequest(BaseModel):
    name: str
    grade: str = ""
    section: str = ""


class ResponseRequest(BaseModel):
    student_id: str
    correct: bool | None = None
    answer: str = ""


@router.get("/join/{code}")
def get_session_by_code(code: str):
    session = store.get_session_by_code(code.upper())
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Check the code and try again.")
    activity = store.get_activity(session["activity_id"])
    return {"session": session, "activity": {"id": activity["id"], "title": activity["title"]}}


@router.post("/join/{code}")
async def join_session(code: str, payload: JoinRequest):
    session = store.get_session_by_code(code.upper())
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Check the code and try again.")
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="This session has ended")
    student = store.add_student_to_session(session["id"], payload.name, payload.grade, payload.section)
    await manager.broadcast(session["code"], {"type": "student_joined", "student": student})
    return {"student": student, "session": session}


@router.post("/join/{code}/response")
async def submit_response(code: str, payload: ResponseRequest):
    session = store.get_session_by_code(code.upper())
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    response = store.add_response(session["id"], payload.student_id, payload.correct, payload.answer)
    await manager.broadcast(session["code"], {"type": "response_submitted", "response": response})
    return response


@router.websocket("/ws/session/{code}")
async def session_ws(websocket: WebSocket, code: str):
    code = code.upper()
    await manager.connect(code, websocket)
    try:
        while True:
            # Teacher dashboard doesn't send anything; this just keeps the socket alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(code, websocket)
