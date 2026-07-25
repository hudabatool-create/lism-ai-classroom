"""Prompt Library: only prompts that generate LISM-compatible HTML activities
live here (per the product spec, general-purpose prompts belong in a
separate toolkit). The two official master prompts are read straight from
the same files ai_service.py uses for real generation -- a single source of
truth -- and merged with each teacher's own saved/favorited prompts.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_teacher
from app.services.ai_service import PROMPTS_DIR
from app.services.data_store import store

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

_BUILTIN_PROMPTS = [
    {
        "id": "builtin-lesson-deck",
        "title": "Interactive Lesson Deck (Master Prompt v3)",
        "category": "All Subjects",
        "activity_type": "Interactive Lesson Deck",
        "file": "lesson_deck_master_prompt.txt",
    },
    {
        "id": "builtin-worksheet",
        "title": "Interactive Worksheet (Master Prompt v1)",
        "category": "All Subjects",
        "activity_type": "Interactive Worksheet",
        "file": "worksheet_master_prompt.txt",
    },
]


def _builtin_prompts() -> list[dict]:
    prompts = []
    for entry in _BUILTIN_PROMPTS:
        body = (PROMPTS_DIR / entry["file"]).read_text(encoding="utf-8")
        prompts.append({
            "id": entry["id"],
            "teacher_id": None,
            "title": entry["title"],
            "category": entry["category"],
            "activity_type": entry["activity_type"],
            "body": body,
            "is_favorite": False,
            "is_builtin": True,
            "created_at": None,
            "updated_at": None,
        })
    return prompts


@router.get("")
def list_prompts(teacher: dict = Depends(get_current_teacher)):
    custom = [{**p, "is_builtin": False} for p in store.list_prompts(teacher["id"])]
    return _builtin_prompts() + custom


class PromptRequest(BaseModel):
    title: str
    category: str = ""
    activity_type: str = "Interactive Lesson Deck"
    body: str


@router.post("")
def create_prompt(payload: PromptRequest, teacher: dict = Depends(get_current_teacher)):
    prompt = store.create_prompt(teacher["id"], payload.title, payload.category, payload.activity_type, payload.body)
    return {**prompt, "is_builtin": False}


def _get_owned_prompt(prompt_id: str, teacher: dict) -> dict:
    if prompt_id.startswith("builtin-"):
        raise HTTPException(status_code=400, detail="Built-in prompts can't be modified")
    prompt = store.get_prompt(prompt_id)
    if not prompt or prompt["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.patch("/{prompt_id}")
def update_prompt(prompt_id: str, payload: PromptRequest, teacher: dict = Depends(get_current_teacher)):
    _get_owned_prompt(prompt_id, teacher)
    prompt = store.update_prompt(prompt_id, payload.title, payload.category, payload.activity_type, payload.body)
    return {**prompt, "is_builtin": False}


@router.post("/{prompt_id}/favorite")
def toggle_favorite(prompt_id: str, teacher: dict = Depends(get_current_teacher)):
    prompt = _get_owned_prompt(prompt_id, teacher)
    updated = store.set_prompt_favorite(prompt_id, not prompt["is_favorite"])
    return {**updated, "is_builtin": False}


@router.delete("/{prompt_id}")
def delete_prompt(prompt_id: str, teacher: dict = Depends(get_current_teacher)):
    _get_owned_prompt(prompt_id, teacher)
    store.delete_prompt(prompt_id)
    return {"deleted": True}
