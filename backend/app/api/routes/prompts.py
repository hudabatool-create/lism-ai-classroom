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

# Every prompt a teacher can copy. The two full-lesson prompts keep the whole
# ALL/MOST/SOME + DOK framework; the rest are single-purpose activities with
# their own natural structure. All of them cover every subject including
# Arabic (RTL, diacritic normalisation) and carry the LISM manifest contract,
# so an activity built from any of them uploads and is teacher-paced.
#
# The version numbers here must match the files -- these titles once read v3
# and v1 while the files were already v10 and v8, which is exactly the kind of
# drift that makes a teacher think they have the wrong prompt.
_BUILTIN_PROMPTS = [
    # --- Full lesson frameworks -------------------------------------------
    {
        "id": "builtin-lesson-deck",
        "title": "Interactive Lesson Deck (Master Prompt v10)",
        "category": "Full Lesson",
        "activity_type": "Interactive Lesson Deck",
        "file": "lesson_deck_master_prompt.txt",
    },
    {
        "id": "builtin-worksheet",
        "title": "Interactive Worksheet (Master Prompt v8)",
        "category": "Full Lesson",
        "activity_type": "Interactive Worksheet",
        "file": "worksheet_master_prompt.txt",
    },
    # --- Single-purpose activities ----------------------------------------
    {"id": "builtin-starter", "title": "Starter / Retrieval Activity", "category": "Lesson Phase",
     "activity_type": "Starter Activity", "file": "starter_prompt.txt"},
    {"id": "builtin-poll", "title": "Poll / Exit Ticket", "category": "Lesson Phase",
     "activity_type": "Poll", "file": "poll_prompt.txt"},
    {"id": "builtin-quiz", "title": "Quiz", "category": "Assessment",
     "activity_type": "Quiz", "file": "quiz_prompt.txt"},
    {"id": "builtin-mcq", "title": "Multiple Choice Questions", "category": "Assessment",
     "activity_type": "Multiple Choice", "file": "mcq_prompt.txt"},
    {"id": "builtin-true-false", "title": "True / False with Justification", "category": "Assessment",
     "activity_type": "True/False", "file": "true_false_prompt.txt"},
    {"id": "builtin-matching", "title": "Matching Activity", "category": "Interactive",
     "activity_type": "Matching", "file": "matching_prompt.txt"},
    {"id": "builtin-drag-drop", "title": "Drag & Drop Activity", "category": "Interactive",
     "activity_type": "Drag & Drop", "file": "drag_drop_prompt.txt"},
    {"id": "builtin-flashcards", "title": "Flashcards", "category": "Interactive",
     "activity_type": "Flashcards", "file": "flashcards_prompt.txt"},
    {"id": "builtin-crossword", "title": "Crossword", "category": "Interactive",
     "activity_type": "Crossword", "file": "crossword_prompt.txt"},
    {"id": "builtin-brainstorm", "title": "Brainstorm Board", "category": "Thinking",
     "activity_type": "Brainstorm Board", "file": "brainstorm_prompt.txt"},
    {"id": "builtin-game", "title": "Learning Game", "category": "Games",
     "activity_type": "Learning Game", "file": "game_prompt.txt"},
    {"id": "builtin-escape-room", "title": "Escape Room", "category": "Games",
     "activity_type": "Escape Room", "file": "escape_room_prompt.txt"},
    {"id": "builtin-simulation", "title": "Simulation", "category": "Exploration",
     "activity_type": "Simulation", "file": "simulation_prompt.txt"},
    {"id": "builtin-coding", "title": "Coding Challenge", "category": "Exploration",
     "activity_type": "Coding Challenge", "file": "coding_challenge_prompt.txt"},
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
