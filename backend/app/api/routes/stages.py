"""Teacher-controlled lesson pacing: the HTML never advances itself:
the teacher starts a stage, LISM broadcasts it to every connected
device, and the class only moves on when the teacher says so."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_teacher
from app.services.data_store import astore, store
from app.services.status_service import broadcast_status_update
from app.services.websocket_manager import manager

router = APIRouter(prefix="/api/sessions", tags=["stages"])


def _get_owned_session(session_id: str, teacher: dict) -> dict:
    session = store.get_session(session_id)
    if not session or session["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


class ExtendRequest(BaseModel):
    additional_seconds: int = 60


@router.post("/{session_id}/stage/start")
async def start_stage(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session = _get_owned_session(session_id, teacher)
    activity = await astore.get_activity(session["activity_id"])
    stages = activity["manifest"]["stages"]
    next_index = session["current_stage_index"] + 1
    if next_index >= len(stages):
        raise HTTPException(status_code=400, detail="This is already the last stage")
    stage = stages[next_index]
    updated = await astore.start_stage(session_id, next_index, stage["durationSeconds"])
    await manager.broadcast(
        session["code"],
        {
            "type": "stage_started",
            "stage": stage,
            "stageIndex": next_index,
            "durationSeconds": stage["durationSeconds"],
            "startedAt": updated["stage_started_at"],
        },
    )
    await broadcast_status_update(updated, activity)
    return updated


@router.post("/{session_id}/stage/end")
async def end_stage(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session = _get_owned_session(session_id, teacher)
    if session["current_stage_index"] < 0:
        raise HTTPException(status_code=400, detail="No stage is running")
    updated = await astore.end_stage(session_id)
    await manager.broadcast(session["code"], {"type": "stage_ended", "stageIndex": updated["current_stage_index"]})
    activity = await astore.get_activity(updated["activity_id"])
    await broadcast_status_update(updated, activity)
    return updated


@router.post("/{session_id}/stage/pause")
async def pause_stage(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session = _get_owned_session(session_id, teacher)
    if session["stage_status"] != "running":
        raise HTTPException(status_code=400, detail="No stage is running")
    updated = await astore.pause_stage(session_id)
    # Students need this too: their page relays it into the activity as a
    # lism:command pause, which freezes inputs without losing typed work.
    await manager.broadcast(
        session["code"],
        {
            "type": "stage_paused",
            "stageIndex": updated["current_stage_index"],
            "remainingSeconds": updated["stage_duration_seconds"],
        },
    )
    activity = await astore.get_activity(updated["activity_id"])
    await broadcast_status_update(updated, activity)
    return updated


@router.post("/{session_id}/stage/resume")
async def resume_stage(session_id: str, teacher: dict = Depends(get_current_teacher)):
    session = _get_owned_session(session_id, teacher)
    if session["stage_status"] != "paused":
        raise HTTPException(status_code=400, detail="This stage is not paused")
    updated = await astore.resume_stage(session_id)
    await manager.broadcast(
        session["code"],
        {
            "type": "stage_resumed",
            "stageIndex": updated["current_stage_index"],
            "durationSeconds": updated["stage_duration_seconds"],
            "startedAt": updated["stage_started_at"],
        },
    )
    activity = await astore.get_activity(updated["activity_id"])
    await broadcast_status_update(updated, activity)
    return updated


@router.post("/{session_id}/stage/extend")
async def extend_stage(session_id: str, payload: ExtendRequest, teacher: dict = Depends(get_current_teacher)):
    session = _get_owned_session(session_id, teacher)
    if session["current_stage_index"] < 0:
        raise HTTPException(status_code=400, detail="No stage is running")
    updated = await astore.extend_stage(session_id, payload.additional_seconds)
    await manager.broadcast(
        session["code"],
        {"type": "timer_extended", "durationSeconds": updated["stage_duration_seconds"]},
    )
    return updated
