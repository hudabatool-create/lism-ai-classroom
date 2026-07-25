"""Computes each student's live status for the teacher dashboard, and
broadcasts it as a single source of truth so the frontend never has to
re-derive it from raw events. Recomputed and rebroadcast after any action
that could change it: join, response, stage start/end, WebSocket
connect/disconnect, a focus violation, or a help request.
"""

from app.services.data_store import store
from app.services.websocket_manager import manager

STATUS_PRIORITY = ("locked", "inactive", "needs_help", "completed", "working", "waiting")


def compute_student_statuses(session: dict, activity: dict) -> dict[str, dict]:
    stages = activity["manifest"]["stages"]
    stage_id = None
    if 0 <= session["current_stage_index"] < len(stages):
        stage_id = stages[session["current_stage_index"]]["id"]

    online_ids = manager.online_student_ids(session["code"])
    responses = store.list_responses(session["id"])
    responded_current_stage = {r["student_id"] for r in responses if r["stage_id"] == stage_id} if stage_id else set()

    statuses: dict[str, dict] = {}
    for student in store.list_students(session["id"]):
        sid = student["id"]
        violation_count = store.get_violation_count(session["id"], sid)

        if violation_count >= 3:
            status = "locked"
        elif sid not in online_ids:
            status = "inactive"
        elif student.get("needs_help"):
            status = "needs_help"
        elif stage_id and sid in responded_current_stage:
            status = "completed"
        elif stage_id and session["stage_status"] == "running":
            status = "working"
        else:
            status = "waiting"

        statuses[sid] = {
            "status": status,
            "violation_count": violation_count,
            "help_requests": student.get("help_requests", 0),
        }
    return statuses


def summarize_statuses(statuses: dict[str, dict]) -> dict[str, int]:
    summary = {key: 0 for key in STATUS_PRIORITY}
    for info in statuses.values():
        summary[info["status"]] = summary.get(info["status"], 0) + 1
    return summary


async def broadcast_status_update(session: dict, activity: dict) -> None:
    # Contains every student's id, violation count and help-request count --
    # teacher-only, never broadcast to students.
    statuses = compute_student_statuses(session, activity)
    await manager.broadcast(
        session["code"],
        {
            "type": "status_update",
            "statuses": statuses,
            "summary": summarize_statuses(statuses),
        },
        roles=("teacher",),
    )
