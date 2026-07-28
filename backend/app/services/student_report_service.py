"""Builds the Lesson Progress Report a student sees when the teacher ends
the lesson.

Every figure comes from what the student actually did -- responses recorded,
stages reached, marks awarded. Nothing is estimated into existence: where a
value genuinely isn't known (an activity with no marks, a stage the student
never reached) the report says so rather than showing a confident zero, which
would read to a child as "you scored nothing".
"""

from datetime import datetime

from app.services.data_store import store
from app.services.scoring import score_student


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _time_spent_seconds(student: dict, session: dict) -> int | None:
    """From when this student joined to when the lesson ended (or now, if it
    is still running). LISM owns this: the activity has no timer of its own."""
    joined = _parse(student.get("joined_at"))
    if joined is None:
        return None
    ended = _parse(session.get("ended_at")) or datetime.now(joined.tzinfo)
    return max(0, int((ended - joined).total_seconds()))


def build_student_report(session: dict, activity: dict, student: dict) -> dict:
    manifest = activity["manifest"] if activity else {}
    stages = manifest.get("stages") or []
    responses = store.list_student_responses(session["id"], student["id"])

    answered_stage_ids = {r["stage_id"] for r in responses if r.get("stage_id")}
    stages_completed = sum(1 for s in stages if s["id"] in answered_stage_ids)

    score = score_student(stages, responses)

    correct_count = sum(1 for r in responses if r.get("correct") is True)
    graded_count = sum(1 for r in responses if r.get("correct") is not None)

    violations = store.get_violation_count(session["id"], student["id"])

    return {
        "activity_title": activity.get("title") if activity else "",
        "subject": manifest.get("subject") or (activity.get("subject") if activity else ""),
        "topic": manifest.get("topic") or (activity.get("title") if activity else ""),
        "grade": manifest.get("grade") or (activity.get("grade") if activity else ""),
        "student_name": student["name"],
        "lesson_completed": session.get("status") == "ended",
        "completion_status": _completion_status(stages_completed, len(stages)),
        "stages_completed": stages_completed,
        "stages_total": len(stages),
        "stage_breakdown": [
            {
                "label": b["label"],
                "completed": b["stage_id"] in answered_stage_ids,
                "marks": b["marks"],
                "awarded": b["awarded"],
                "status": b["status"],
            }
            for b in score["stages"]
        ],
        # None (not 0) when the activity awards no marks, so the UI can say
        # "not scored" instead of implying the student earned nothing.
        "estimated_score": score["awarded_total"],
        "max_score": score["max_score"],
        "auto_scored": score["auto_scored"],
        "teacher_scored": score["teacher_scored"],
        "pending_review": score["pending_review"],
        "responses_submitted": len(responses),
        "answered_correctly": correct_count,
        "auto_graded_count": graded_count,
        "help_requests": student.get("help_requests", 0),
        "focus_warnings": violations,
        "time_spent_seconds": _time_spent_seconds(student, session),
        "teacher_review_pending": not score["fully_graded"],
        "teacher_review_message": _review_message(score),
    }


def _review_message(score: dict) -> str:
    """What the student is told about their score.

    Never promises a number that might not arrive: a teacher may choose not to
    mark the starter at all, and a child told "you will be graded" who then
    sees nothing learns that the message means nothing.
    """
    if not score["max_score"]:
        return "This activity isn't marked. Your teacher can still see everything you wrote."
    if score["fully_graded"]:
        return "Your teacher has reviewed and marked your work."
    return (
        "Your teacher will see and review your work. "
        "Any score shown here so far is from the parts that mark themselves."
    )


def _completion_status(done: int, total: int) -> str:
    if total == 0:
        return "Completed"
    if done == 0:
        return "Not started"
    if done >= total:
        return "Completed"
    return "Partly completed"
