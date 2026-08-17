import io

import qrcode
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_current_teacher
from app.core.config import settings
from app.core.security import decode_access_token
from app.services.data_store import astore, store
from app.services.scoring import score_student
from app.services.status_service import broadcast_status_update, compute_student_statuses, summarize_statuses
from app.services.student_report_service import build_student_report
from app.services.websocket_manager import manager

router = APIRouter(prefix="/api", tags=["sessions"])

# Generated in the browser via Web Audio -- no audio files to host, and it
# still works with no network.
TIMER_SOUNDS = ("none", "chime", "bell", "school_bell")


def _join_url(code: str) -> str:
    return f"{settings.canonical_origin}/join/{code}"


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
        "server_time": datetime.now(timezone.utc).isoformat(),
        "online_student_ids": list(manager.online_student_ids(session["code"])),
        "student_statuses": statuses,
        "status_summary": summarize_statuses(statuses),
        "focus_violations": focus_violations,
    }


@router.get("/sessions/{session_id}/marks")
def session_marks(session_id: str, teacher: dict = Depends(get_current_teacher)):
    """Everything the marking panel needs, in one round trip.

    One entry per student with their per-stage breakdown, so the teacher sees
    the answer, what the activity already scored, and what they still owe --
    without the page having to stitch responses to stages itself.
    """
    session = store.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")

    activity = store.get_activity(session["activity_id"])
    stages = activity["manifest"]["stages"] if activity else []
    responses = store.list_responses(session_id)
    by_student: dict[str, list[dict]] = {}
    for r in responses:
        by_student.setdefault(r["student_id"], []).append(r)

    students = []
    for student in store.list_students(session_id):
        score = score_student(stages, by_student.get(student["id"], []))
        students.append({
            "student_id": student["id"],
            "name": student["name"],
            "grade": student.get("grade", ""),
            "section": student.get("section", ""),
            **score,
        })

    marked_stages = [
        {"id": s["id"], "label": s["label"], "marks": s["marks"],
         "auto_marks": s.get("autoMarks"), "teacher_marks": s.get("teacherMarks"),
         "rubric": s.get("rubric") or []}
        for s in stages if s.get("marks")
    ]
    return {
        "activity_title": activity["title"] if activity else "",
        "session_code": session["code"],
        "total_marks": sum(s["marks"] for s in marked_stages) or None,
        "stages": marked_stages,
        "students": students,
        "awaiting_review": sum(1 for s in students if not s["fully_graded"]),
    }


class GradeRequest(BaseModel):
    student_id: str
    stage_id: str
    # None clears the mark back to ungraded. Bare `float | None` with no
    # default would still require the key, which is what we want: an omitted
    # mark is almost always a bug, an explicit null is a deliberate undo.
    mark: float | None
    feedback: str | None = None


@router.post("/sessions/{session_id}/grade")
def grade_response(session_id: str, payload: GradeRequest, teacher: dict = Depends(get_current_teacher)):
    """Record the teacher's own mark for a stage the activity can't score.

    Deliberately teacher-only and session-scoped: this is the number that
    reaches the gradebook, so it can't be settable from a student's device.
    """
    session = store.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")

    activity = store.get_activity(session["activity_id"])
    stages = activity["manifest"]["stages"] if activity else []
    stage = next((s for s in stages if s["id"] == payload.stage_id), None)
    if stage is None:
        raise HTTPException(status_code=404, detail="That stage isn't part of this activity")

    if payload.mark is not None:
        if payload.mark < 0:
            raise HTTPException(status_code=400, detail="A mark can't be negative")
        # Bounded by what the stage is actually worth, so a slip of the
        # keyboard can't put 50 into a stage worth 5.
        ceiling = stage.get("marks")
        if ceiling is not None and payload.mark > ceiling:
            raise HTTPException(
                status_code=400,
                detail=f'"{stage["label"]}" is out of {ceiling:g} marks',
            )

    graded = store.set_teacher_mark(
        session_id, payload.student_id, payload.stage_id, payload.mark, payload.feedback
    )
    if graded is None:
        raise HTTPException(status_code=404, detail="That student hasn't answered this stage")
    return graded


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
    timer_sound: str | None = None


@router.patch("/sessions/{session_id}/settings")
async def update_session_settings(
    session_id: str, payload: SessionSettingsRequest, teacher: dict = Depends(get_current_teacher)
):
    """Teacher toggles copy-paste protection / focus monitoring mid-lesson.
    Broadcast to everyone so student pages re-send set_config into their
    activity iframe without needing a reload."""
    session = await astore.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.max_warnings is not None and not 1 <= payload.max_warnings <= 10:
        raise HTTPException(status_code=400, detail="Maximum warnings must be between 1 and 10")
    if payload.timer_sound is not None and payload.timer_sound not in TIMER_SOUNDS:
        raise HTTPException(status_code=400, detail=f"Timer sound must be one of: {', '.join(TIMER_SOUNDS)}")
    updated = await astore.update_session_settings(
        session_id,
        copy_paste_protection=payload.copy_paste_protection,
        focus_monitoring=payload.focus_monitoring,
        max_warnings=payload.max_warnings,
        timer_sound=payload.timer_sound,
    )
    await manager.broadcast(
        updated["code"],
        {
            "type": "settings_updated",
            "copyPasteProtection": updated["copy_paste_protection"],
            "focusMonitoring": updated["focus_monitoring"],
            "maxWarnings": updated["max_warnings"],
            "timerSound": updated["timer_sound"],
        },
    )
    return updated


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session = await astore.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    ended = await astore.end_session(session_id)
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
    # True when `answer` is the whole section read at once, so it already
    # contains everything sent before and should overwrite it. False when the
    # activity is reporting one more question of its own, which is appended.
    replace: bool = False


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
        # The countdown is derived from when the stage started, and every
        # device was measuring that against its own clock. A phone seven
        # seconds out from the teacher's laptop showed a countdown seven
        # seconds out, and neither person could tell which was right. Sending
        # the server's own time lets each device correct for its offset, so
        # everyone counts down from the same clock.
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/join/{code}")
async def join_session(code: str, payload: JoinRequest):
    session = await astore.get_session_by_code(code.upper())
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Check the code and try again.")
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="This session has ended")
    student, rejoined = await astore.add_student_to_session(session["id"], payload.name, payload.grade, payload.section)
    # Only announce genuinely new participants -- a reconnecting student is
    # already on the teacher's list and shouldn't appear to join twice.
    if not rejoined:
        await manager.broadcast(session["code"], {"type": "student_joined", "student": student}, roles=("teacher",))
    activity = await astore.get_activity(session["activity_id"])
    await broadcast_status_update(session, activity)
    return {
        "student": student,
        "session": session,
        "rejoined": rejoined,
        "responses": await astore.list_student_responses(session["id"], student["id"]),
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
    if await astore.is_locked(session["id"], payload.student_id):
        raise HTTPException(status_code=403, detail="This activity is locked due to focus violations")
    activity = await astore.get_activity(session["activity_id"])
    stage_id = payload.stage_id
    if not stage_id:
        stages = activity["manifest"]["stages"]
        stage_index = session["current_stage_index"] if session["current_stage_index"] >= 0 else 0
        stage_id = stages[stage_index]["id"]
    # Teacher-controlled pacing has to be enforced here, not in the activity.
    # A worksheet is one long scrolling page: every section is on screen at
    # once, so a student can always reach the Exit Ticket and type in it, and
    # an uploaded activity that ignores our stage commands can't be made to
    # hide anything. The server is the only place the rule can actually hold.
    stages = activity["manifest"]["stages"]
    stage_index = next((i for i, s in enumerate(stages) if s["id"] == stage_id), None)
    if stage_index is None:
        raise HTTPException(status_code=400, detail="That section is not part of this activity")
    if stage_index > session["current_stage_index"]:
        label = stages[stage_index]["label"]
        raise HTTPException(
            status_code=403,
            detail=f"Your teacher hasn't started \"{label}\" yet. Your answer was not saved — wait for this section to begin.",
        )

    # A stage is rarely one question. Treating the first submission as final
    # showed the teacher only question one of a five-question Exit Ticket, and
    # a single line of a ten-mark Main Task -- so later work now updates the
    # same row rather than being refused. See add_response for the two modes.
    response = await astore.add_response(
        session["id"], payload.student_id, stage_id, payload.correct,
        payload.answer, payload.mark, replace=payload.replace,
    )
    await astore.set_needs_help(payload.student_id, False)
    await manager.broadcast(session["code"], {"type": "response_submitted", "response": response}, roles=("teacher",))
    await broadcast_status_update(session, activity)
    return response


class FocusViolationRequest(BaseModel):
    student_id: str
    type: str = "tab_switch"


@router.post("/join/{code}/focus-violation")
async def report_focus_violation(code: str, payload: FocusViolationRequest):
    session = active_session_for_student(code, payload.student_id)
    violation = await astore.add_focus_violation(session["id"], payload.student_id, payload.type)
    # Ask the store, rather than counting the raw total. A student the teacher
    # has already let back in starts from three again, not from wherever their
    # running total happens to be -- otherwise unlocking someone would last
    # exactly one tab switch.
    locked = await astore.is_locked(session["id"], payload.student_id)
    await manager.broadcast(
        session["code"], {"type": "focus_violation", "violation": violation, "locked": locked}, roles=("teacher",)
    )
    activity = await astore.get_activity(session["activity_id"])
    await broadcast_status_update(session, activity)
    return {"violation_number": violation["violation_number"], "locked": locked}


class UnlockRequest(BaseModel):
    student_id: str


@router.post("/sessions/{session_id}/unlock")
async def unlock_student(
    session_id: str, payload: UnlockRequest, teacher: dict = Depends(get_current_teacher)
):
    """Let a student back into the lesson after a focus lock.

    Three tab switches locked a student out with no way back: not by the
    teacher, not by rejoining, not by anything. A child who lost their
    connection, or picked up a genuine notification, sat out the rest of the
    lesson while the class carried on. Whether that is the right outcome is a
    judgement for the teacher in the room, and they had no way to make it.

    Teacher-only and scoped to their own session, because this is the control
    that undoes an integrity measure -- it must not be reachable from the
    device that got locked.
    """
    session = await astore.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")

    forgiven = await astore.forgive_violations(session_id, payload.student_id)
    await manager.send_to_student(
        session["code"], payload.student_id, {"type": "focus_unlocked"}
    )
    activity = await astore.get_activity(session["activity_id"])
    await broadcast_status_update(session, activity)
    await manager.broadcast(
        session["code"],
        {"type": "student_unlocked", "student_id": payload.student_id},
        roles=("teacher",),
    )
    return {"unlocked": True, "violations_forgiven": forgiven}


class NeedHelpRequest(BaseModel):
    student_id: str


@router.post("/join/{code}/need-help")
async def request_help(code: str, payload: NeedHelpRequest):
    session = active_session_for_student(code, payload.student_id)
    student = await astore.set_needs_help(payload.student_id, True)
    await manager.broadcast(session["code"], {"type": "need_help_requested", "student": student}, roles=("teacher",))
    activity = await astore.get_activity(session["activity_id"])
    await broadcast_status_update(session, activity)
    return {"help_requests": student["help_requests"]}


@router.websocket("/ws/session/{code}")
async def session_ws(
    websocket: WebSocket,
    code: str,
    student_id: str | None = Query(default=None),
):
    code = code.upper()
    session = await astore.get_session_by_code(code)
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
        teacher = await astore.get_teacher(auth_payload["sub"]) if auth_payload else None
        if not session or not teacher or teacher["id"] != session["teacher_id"]:
            await websocket.close(code=4401)
            return

    await manager.connect(code, websocket, role, student_id)
    if role == "student":
        await manager.broadcast(code, {"type": "student_online", "student_id": student_id}, roles=("teacher",))
    if session:
        activity = await astore.get_activity(session["activity_id"])
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
            activity = await astore.get_activity(session["activity_id"])
            await broadcast_status_update(session, activity)
