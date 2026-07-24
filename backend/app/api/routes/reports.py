import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.api.deps import get_current_teacher
from app.services.data_store import store
from app.services.report_service import build_csv, build_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _load(session_id: str, teacher: dict):
    session = store.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    activity = store.get_activity(session["activity_id"])
    students = store.list_students(session_id)
    responses = store.list_responses(session_id)
    return session, activity, students, responses


@router.get("/{session_id}/pdf")
def report_pdf(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session, activity, students, responses = _load(session_id, teacher)
    pdf_bytes = build_pdf(session, activity, students, responses)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report-{session['code']}.pdf"},
    )


@router.get("/{session_id}/csv")
def report_csv(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session, activity, students, responses = _load(session_id, teacher)
    csv_text = build_csv(session, activity, students, responses)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report-{session['code']}.csv"},
    )
