from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_teacher
from app.services.data_store import store
from app.services.insights_service import build_insights

router = APIRouter(prefix="/api/sessions", tags=["insights"])


@router.get("/{session_id}/insights")
def get_insights(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session = store.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    activity = store.get_activity(session["activity_id"])
    students = store.list_students(session_id)
    responses = store.list_responses(session_id)
    focus_violations = store.list_focus_violations(session_id)
    return build_insights(activity, students, responses, focus_violations)
