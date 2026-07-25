import mimetypes

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.api.deps import get_current_teacher
from app.services.ai_service import generate_activity_html
from app.services.data_store import store
from app.services.manifest_service import extract_manifest
from app.services.zip_service import extract_zip_activity

router = APIRouter(prefix="/api/activities", tags=["activities"])


def _public_activity(activity: dict) -> dict:
    """Activity dicts hold raw asset bytes (from a ZIP upload) which can't be
    JSON-serialized and shouldn't be sent to the client anyway -- replace
    them with just the list of asset filenames."""
    return {**{k: v for k, v in activity.items() if k != "assets"}, "asset_files": sorted(activity.get("assets") or {})}


@router.get("")
def list_activities(teacher: dict = Depends(get_current_teacher)):
    return [_public_activity(a) for a in store.list_activities(teacher["id"])]


@router.post("/upload")
async def upload_activity(
    title: str = Form(...),
    subject: str = Form(""),
    grade: str = Form(""),
    activity_type: str = Form("Custom Upload"),
    file: UploadFile = File(...),
    teacher: dict = Depends(get_current_teacher),
):
    filename = (file.filename or "").lower()
    raw = await file.read()
    assets: dict[str, bytes] = {}

    if filename.endswith(".zip"):
        try:
            html, assets = extract_zip_activity(raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    elif filename.endswith((".html", ".htm")):
        html = raw.decode("utf-8", errors="replace")
    else:
        raise HTTPException(status_code=400, detail="Only .html, .htm, or .zip files are supported")

    manifest = extract_manifest(html, fallback_title=title)
    activity = store.create_activity(
        teacher_id=teacher["id"],
        title=title,
        subject=subject,
        grade=grade,
        activity_type=activity_type,
        html=html,
        source="upload",
        manifest=manifest,
        assets=assets,
    )
    return _public_activity(activity)


class GenerateRequest(BaseModel):
    subject: str
    grade: str
    topic: str
    activity_type: str
    objectives: str = ""
    difficulty: str = "Medium"
    time_limit: int = 10
    custom_prompt: str | None = None


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
        payload.custom_prompt,
    )
    manifest = extract_manifest(html, fallback_title=payload.topic)
    activity = store.create_activity(
        teacher_id=teacher["id"],
        title=payload.topic,
        subject=payload.subject,
        grade=payload.grade,
        activity_type=payload.activity_type,
        html=html,
        source="ai",
        manifest=manifest,
    )
    return _public_activity(activity)


@router.get("/{activity_id}/raw", response_class=HTMLResponse)
def raw_activity(activity_id: str):
    """Public: students load the activity itself with no auth required."""
    activity = store.get_activity(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return HTMLResponse(activity["html"])


@router.get("/{activity_id}/{asset_path:path}")
def activity_asset(activity_id: str, asset_path: str):
    """Public: serves the CSS/JS/image files from a ZIP-uploaded activity.
    A browser resolves an entry HTML's relative references (e.g.
    "style.css") against the directory of the /raw URL that served it, so
    this route must live at exactly this path -- not nested under an extra
    prefix -- and must be registered after /raw so that exact route keeps
    matching "raw" instead of falling through to this catch-all."""
    activity = store.get_activity(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    asset = (activity.get("assets") or {}).get(asset_path)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    media_type, _ = mimetypes.guess_type(asset_path)
    return Response(content=asset, media_type=media_type or "application/octet-stream")
