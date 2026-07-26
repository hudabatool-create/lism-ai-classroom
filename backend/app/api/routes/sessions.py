import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_current_teacher
from app.core.config import settings
from app.core.security import decode_access_token
from app.services.data_store import store
from app.services.status_service import broadcast_status_update, compute_student_statuses, summarize_statuses
from app.services.student_report_service import build_student_report
from app.services.websocket_manager import manager

router = APIRouter(prefix="/api", tags=["sessions"])


def _join_url(code: str) -> str:
    return f"{settings.frontend_origin}/join/{code}"


# --- Teacher-facing ---------------------------------------------------


@router.post("/activities/{activity_id}/launch")
def launch_session(activity_id: str, session_type: str = "lesson", teacher: dict = Depends(get_current_teacher)):
    activity = store.get_activity(activity_id)
    if not activity or activity["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Activity not found")
    session = store.create_session(teacher["id"], activity_id, session_type)
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
    # Loaded once and passed down -- compute_student_statuses would otherwise
    # re-query both, doubling the round-trips on the busiest endpoint here.
    responses = store.list_responses(session_id)
    students = store.list_students(session_id)
    focus_violations = store.list_focus_violations(session_id)
    current_stage = None
    if activity and session["current_stage_index"] >= 0:
        current_stage = activity["manifest"]["stages"][session["current_stage_index"]]
    statuses = compute_student_statuses(
        session, activity, students=students, responses=responses, violations=focus_violations
    )
    return {
        "session": {**session, "join_url": _join_url(session["code"])},
        # Strip raw asset bytes (from a ZIP-uploaded activity) -- they can't
        # be JSON-serialized and the teacher dashboard doesn't need them.
        "activity": {k: v for k, v in activity.items() if k != "assets"} if activity else None,
        "students": students,
        "responses": responses,
        "current_stage": current_stage,
        "online_student_ids": list(manager.online_student_ids(session["code"])),
        "student_statuses": statuses,
        "status_summary": summarize_statuses(statuses),
        "focus_violations": focus_violations,
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


class SessionSettingsRequest(BaseModel):
    copy_paste_protection: bool | None = None
    focus_monitoring: bool | None = None
    max_warnings: int | None = None


@router.patch("/sessions/{session_id}/settings")
async def update_session_settings(
    session_id: str, payload: SessionSettingsRequest, teacher: dict = Depends(get_current_teacher)
):
    """Teacher toggles copy-paste protection / focus monitoring mid-lesson.
    Broadcast to everyone so student pages re-send set_config into their
    activity iframe without needing a reload."""
    session = store.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.max_warnings is not None and not 1 <= payload.max_warnings <= 10:
        raise HTTPException(status_code=400, detail="Maximum warnings must be between 1 and 10")
    updated = store.update_session_settings(
        session_id,
        copy_paste_protection=payload.copy_paste_protection,
        focus_monitoring=payload.focus_monitoring,
        max_warnings=payload.max_warnings,
    )
    await manager.broadcast(
        updated["code"],
        {
            "type": "settings_updated",
            "copyPasteProtection": updated["copy_paste_protection"],
            "focusMonitoring": updated["focus_monitoring"],
            "maxWarnings": updated["max_warnings"],
        },
    )
    return updated


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session = store.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    ended = store.end_session(session_id)
    # Students were previously told nothing when the lesson ended -- they just
    # sat on a frozen activity. This is what triggers their report.
    await manager.broadcast(ended["code"], {"type": "session_ended"})
    return ended


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
    student, rejoined = store.add_student_to_session(session["id"], payload.name, payload.grade, payload.section)
    # Only announce genuinely new participants -- a reconnecting student is
    # already on the teacher's list and shouldn't appear to join twice.
    if not rejoined:
        await manager.broadcast(session["code"], {"type": "student_joined", "student": student}, roles=("teacher",))
    activity = store.get_activity(session["activity_id"])
    await broadcast_status_update(session, activity)
    return {
        "student": student,
        "session": session,
        "rejoined": rejoined,
        "responses": store.list_student_responses(session["id"], student["id"]),
    }


@router.get("/join/{code}/report/{student_id}")
def student_report(code: str, student_id: str):
    """The student's own Lesson Progress Report. Public like the rest of the
    join API -- students never log in -- but scoped to one student in one
    session, so it can't be used to read a classmate's results."""
    session = store.get_session_by_code(code.upper())
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    student = store.get_student_in_session(student_id, session["id"])
    if not student:
        raise HTTPException(status_code=404, detail="Student not found in this session")
    activity = store.get_activity(session["activity_id"])
    return build_student_report(session, activity, student)


@router.get("/join/{code}/student/{student_id}")
def resume_student(code: str, student_id: str):
    """Lets a returning device prove it already belongs to this session, so a
    refresh restores the student instead of asking them to type their name and
    risk becoming a second participant."""
    session = store.get_session_by_code(code.upper())
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    student = store.get_student_in_session(student_id, session["id"])
    if not student:
        raise HTTPException(status_code=404, detail="Student not found in this session")
    return {
        "student": student,
        "session": session,
        "responses": store.list_student_responses(session["id"], student_id),
    }


def active_session_for_student(code: str, student_id: str) -> dict:
    """Shared gate for every student-facing write: the session must exist, be
    still running, and actually contain this student. A student sitting on a
    stale page after the teacher ended the lesson must not keep writing to it.
    """
    session = store.get_session_by_code(code.upper())
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="This session has ended")
    if not store.get_student_in_session(student_id, session["id"]):
        raise HTTPException(status_code=404, detail="Student not found in this session")
    return session


@router.post("/join/{code}/response")
async def submit_response(code: str, payload: ResponseRequest):
    session = active_session_for_student(code, payload.student_id)
    if store.is_locked(session["id"], payload.student_id):
        raise HTTPException(status_code=403, detail="This activity is locked due to focus violations")
    activity = store.get_activity(session["activity_id"])
    stage_id = payload.stage_id
    if not stage_id:
        stages = activity["manifest"]["stages"]
        stage_index = session["current_stage_index"] if session["current_stage_index"] >= 0 else 0
        stage_id = stages[stage_index]["id"]
    if store.has_response_for_stage(session["id"], payload.student_id, stage_id):
        raise HTTPException(status_code=409, detail="You've already submitted an answer for this part of the lesson")
    response = store.add_response(session["id"], payload.student_id, stage_id, payload.correct, payload.answer, payload.mark)
    store.set_needs_help(payload.student_id, False)
    await manager.broadcast(session["code"], {"type": "response_submitted", "response": response}, roles=("teacher",))
    await broadcast_status_update(session, activity)
    return response


class FocusViolationRequest(BaseModel):
    student_id: str
    type: str = "tab_switch"


@router.post("/join/{code}/focus-violation")
async def report_focus_violation(code: str, payload: FocusViolationRequest):
    session = active_session_for_student(code, payload.student_id)
    violation = store.add_focus_violation(session["id"], payload.student_id, payload.type)
    locked = violation["violation_number"] >= 3
    await manager.broadcast(
        session["code"], {"type": "focus_violation", "violation": violation, "locked": locked}, roles=("teacher",)
    )
    activity = store.get_activity(session["activity_id"])
    await broadcast_status_update(session, activity)
    return {"violation_number": violation["violation_number"], "locked": locked}


class NeedHelpRequest(BaseModel):
    student_id: str


@router.post("/join/{code}/need-help")
async def request_help(code: str, payload: NeedHelpRequest):
    session = active_session_for_student(code, payload.student_id)
    student = store.set_needs_help(payload.student_id, True)
    await manager.broadcast(session["code"], {"type": "need_help_requested", "student": student}, roles=("teacher",))
    activity = store.get_activity(session["activity_id"])
    await broadcast_status_update(session, activity)
    return {"help_requests": student["help_requests"]}


@router.websocket("/ws/session/{code}")
async def session_ws(
    websocket: WebSocket,
    code: str,
    student_id: str | None = Query(default=None),
):
    code = code.upper()
    session = store.get_session_by_code(code)
    role = "student" if student_id else "teacher"

    if role == "teacher":
        # Anyone who knows/guesses a session code could otherwise open this
        # connection with no student_id and silently watch every student's
        # name, answers and focus violations with zero proof they're the
        # teacher who owns it. Require and verify their JWT here -- it comes
        # from the httpOnly session cookie, which the browser attaches to the
        # handshake automatically (there's no localStorage token to pass as
        # a query param anymore).
        token = websocket.cookies.get(settings.jwt_cookie_name)
        auth_payload = decode_access_token(token) if token else None
        teacher = store.get_teacher(auth_payload["sub"]) if auth_payload else None
        if not session or not teacher or teacher["id"] != session["teacher_id"]:
            await websocket.close(code=4401)
            return

    await manager.connect(code, websocket, role, student_id)
    if role == "student":
        await manager.broadcast(code, {"type": "student_online", "student_id": student_id}, roles=("teacher",))
    if session:
        activity = store.get_activity(session["activity_id"])
        await broadcast_status_update(session, activity)
    try:
        while True:
            # Neither side sends anything over this socket today; it's just kept
            # alive so the backend can push stage/response events to it.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(code, websocket)
        if role == "student":
            await manager.broadcast(code, {"type": "student_offline", "student_id": student_id}, roles=("teacher",))
        if session:
            activity = store.get_activity(session["activity_id"])
            await broadcast_status_update(session, activity)
