from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.api.deps import get_current_teacher
from app.services.ai_service import generate_activity_html
from app.services.data_store import store

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("")
def list_activities(teacher: dict = Depends(get_current_teacher)):
    return store.list_activities(teacher["id"])


@router.post("/upload")
async def upload_activity(
    title: str = Form(...),
    subject: str = Form(""),
    grade: str = Form(""),
    activity_type: str = Form("Custom Upload"),
    file: UploadFile = File(...),
    teacher: dict = Depends(get_current_teacher),
):
    if not file.filename or not file.filename.lower().endswith((".html", ".htm")):
        raise HTTPException(status_code=400, detail="Only .html/.htm files are supported in this scaffold")
    raw = await file.read()
    html = raw.decode("utf-8", errors="replace")
    return store.create_activity(
        teacher_id=teacher["id"],
        title=title,
        subject=subject,
        grade=grade,
        activity_type=activity_type,
        html=html,
        source="upload",
    )


class GenerateRequest(BaseModel):
    subject: str
    grade: str
    topic: str
    activity_type: str
    objectives: str = ""
    difficulty: str = "Medium"
    time_limit: int = 10


@router.post("/generate")
def generate_activity(payload: GenerateRequest, teacher: dict = Depends(get_current_teacher)):
    html = generate_activity_html(
        payload.subject,
        payload.grade,
        payload.topic,
        payload.activity_type,
        payload.objectives,
        payload.difficulty,
        payload.time_limit,
    )
    return store.create_activity(
        teacher_id=teacher["id"],
        title=payload.topic,
        subject=payload.subject,
        grade=payload.grade,
        activity_type=payload.activity_type,
        html=html,
        source="ai",
    )


@router.get("/{activity_id}/raw", response_class=HTMLResponse)
def raw_activity(activity_id: str):
    """Public: students load the activity itself with no auth required."""
    activity = store.get_activity(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return HTMLResponse(activity["html"])
