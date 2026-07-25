import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
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
    activity = store.get_activity(session["activity_id"])
    responses = store.list_responses(session_id)
    current_stage = None
    if activity and session["current_stage_index"] >= 0:
        current_stage = activity["manifest"]["stages"][session["current_stage_index"]]
    return {
        "session": {**session, "join_url": _join_url(session["code"])},
        "activity": activity,
        "students": store.list_students(session_id),
        "responses": responses,
        "current_stage": current_stage,
        "online_student_ids": list(manager.online_student_ids(session["code"])),
    }


@router.get("/sessions/{session_id}/qrcode.png")
def session_qrcode(session_id: str):
    """Public: rendered via a plain <img> tag on the teacher's live page, which
    can't send an Authorization header. It only ever encodes the join URL,
    which is meant to be shared with the whole class anyway."""
    session = store.get_session(session_id)
    if not session:
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
    stage_id: str | None = None
    correct: bool | None = None
    answer: str = ""
    mark: float | None = None


@router.get("/join/{code}")
def get_session_by_code(code: str):
    session = store.get_session_by_code(code.upper())
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Check the code and try again.")
    activity = store.get_activity(session["activity_id"])
    manifest = activity["manifest"]
    current_stage = manifest["stages"][session["current_stage_index"]] if session["current_stage_index"] >= 0 else None
    return {
        "session": session,
        "activity": {"id": activity["id"], "title": activity["title"], "manifest": manifest},
        "current_stage": current_stage,
    }


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
    activity = store.get_activity(session["activity_id"])
    stage_id = payload.stage_id
    if not stage_id:
        stages = activity["manifest"]["stages"]
        stage_index = session["current_stage_index"] if session["current_stage_index"] >= 0 else 0
        stage_id = stages[stage_index]["id"]
    response = store.add_response(session["id"], payload.student_id, stage_id, payload.correct, payload.answer, payload.mark)
    await manager.broadcast(session["code"], {"type": "response_submitted", "response": response})
    return response


@router.websocket("/ws/session/{code}")
async def session_ws(websocket: WebSocket, code: str, student_id: str | None = Query(default=None)):
    code = code.upper()
    role = "student" if student_id else "teacher"
    await manager.connect(code, websocket, role, student_id)
    if role == "student":
        await manager.broadcast(code, {"type": "student_online", "student_id": student_id})
    try:
        while True:
            # Neither side sends anything over this socket today; it's just kept
            # alive so the backend can push stage/response events to it.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(code, websocket)
        if role == "student":
            await manager.broadcast(code, {"type": "student_offline", "student_id": student_id})
