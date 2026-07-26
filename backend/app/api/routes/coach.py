"""Public, student-facing: the AI Learning Coach. No auth -- students never
log in -- but every message is scoped to a real session + student pair."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.routes.sessions import active_session_for_student
from app.services import ai_coach_service
from app.services.data_store import store
from app.services.status_service import broadcast_status_update
from app.services.websocket_manager import manager

router = APIRouter(prefix="/api/join", tags=["coach"])

COACH_ESCALATION_THRESHOLD = 4


class CoachTurn(BaseModel):
    role: str  # "student" | "coach"
    content: str


class CoachRequest(BaseModel):
    student_id: str
    message: str
    history: list[CoachTurn] = []


@router.post("/{code}/coach")
async def ask_coach(code: str, payload: CoachRequest):
    session = active_session_for_student(code, payload.student_id)

    activity = store.get_activity(session["activity_id"])
    manifest = activity["manifest"]
    current_stage = None
    if 0 <= session["current_stage_index"] < len(manifest["stages"]):
        current_stage = manifest["stages"][session["current_stage_index"]]

    history = [turn.model_dump() for turn in payload.history]
    reply = ai_coach_service.coach_reply(manifest, current_stage, history, payload.message)

    count = store.increment_coach_messages(payload.student_id)

    if count == COACH_ESCALATION_THRESHOLD:
        store.set_needs_help(payload.student_id, True)
        await manager.broadcast(
            session["code"],
            {"type": "coach_escalated", "student_id": payload.student_id, "message_count": count},
            roles=("teacher",),
        )
        await broadcast_status_update(session, activity)

    return {"reply": reply, "message_count": count}
