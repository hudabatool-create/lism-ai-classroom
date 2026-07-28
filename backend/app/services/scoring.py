"""Turns a student's responses into marks, honestly.

One module because three places need this answer -- the student's own report,
the teacher's marking panel, and the exported gradebook -- and they must never
disagree about what a child scored.

The central rule: a mark is only ever reported when someone actually awarded
it. A machine awards marks for objectively markable work (a chosen option, a
matched pair, a passing test). A teacher awards the rest. Anything nobody has
marked yet is reported as *pending*, never as zero, because a zero on a report
is a claim about a student that we would be making up.

So a score is three numbers, not one:

    auto_scored      what the activity could mark on its own
    pending_review   marks a human still owes
    max_score        what the activity is out of

A single number would have to either invent the pending part or silently drop
it, and both lie to whoever reads the report.
"""


def _auto_awarded(stage: dict, response: dict | None) -> float | None:
    """What the activity itself scored for this stage, if anything.

    Returns None when the activity reported nothing markable -- an open
    written answer, or an activity that simply didn't say. None is not zero:
    it means "no machine can judge this", which is what makes it the
    teacher's.
    """
    if response is None:
        return None
    if response.get("mark") is not None:
        return float(response["mark"])
    correct = response.get("correct")
    if correct is True:
        # Full objective portion. A stage that declares no split is treated as
        # entirely objective, which is what a quiz or matching activity is.
        return float(stage.get("autoMarks") or stage.get("marks") or 0)
    if correct is False:
        return 0.0
    return None


def score_stage(stage: dict, response: dict | None) -> dict:
    """One stage's marks for one student."""
    marks = stage.get("marks")
    answered = response is not None
    teacher_mark = response.get("teacher_mark") if response else None

    result = {
        "stage_id": stage["id"],
        "label": stage["label"],
        "marks": marks,
        "auto_marks": stage.get("autoMarks"),
        "teacher_marks": stage.get("teacherMarks"),
        "answered": answered,
        "answer": response.get("answer", "") if response else "",
        "correct": response.get("correct") if response else None,
        "auto_awarded": None,
        "teacher_awarded": teacher_mark,
        "teacher_feedback": response.get("teacher_feedback") if response else None,
        "awarded": None,
        "pending": 0.0,
        "status": "not_marked",
    }

    if not marks:
        # Practice, discussion, reflection -- deliberately unmarked. Flashcards
        # and brainstorm boards live here, and forcing marks onto them would
        # turn thinking aloud into performing.
        result["status"] = "unmarked"
        return result

    if not answered:
        # Still owed, not settled. Whether an unreached stage becomes a zero or
        # is excused (the student was pulled out, the class ran short) is the
        # teacher's call -- so it stays pending until they make it, rather than
        # quietly scoring 0 and marking the student complete.
        result["status"] = "not_answered"
        result["pending"] = float(marks)
        return result

    auto = _auto_awarded(stage, response)
    result["auto_awarded"] = auto

    if teacher_mark is not None:
        # The teacher has seen the work. Their judgement is the mark that
        # travels to the gradebook, whatever the activity thought.
        result["awarded"] = float(teacher_mark)
        result["status"] = "teacher_graded"
        return result

    result["awarded"] = auto
    if auto is None:
        # Nothing could be scored automatically, so the whole stage is owed.
        result["pending"] = float(marks)
    else:
        result["pending"] = float(stage.get("teacherMarks") or 0)
    result["status"] = "pending_review" if result["pending"] else "auto_graded"
    return result


def score_student(stages: list[dict], responses: list[dict]) -> dict:
    """Full mark breakdown for one student across an activity."""
    by_stage = {r["stage_id"]: r for r in responses if r.get("stage_id")}
    breakdown = [score_stage(s, by_stage.get(s["id"])) for s in stages]
    marked = [b for b in breakdown if b["marks"]]

    max_score = sum(b["marks"] for b in marked) or None
    auto_scored = sum(b["awarded"] or 0 for b in marked if b["status"] == "auto_graded")
    teacher_scored = sum(b["awarded"] or 0 for b in marked if b["status"] == "teacher_graded")
    # Partial auto marks on a stage still awaiting a human -- real marks the
    # student has already earned, so they count towards the running total.
    partial = sum(b["awarded"] or 0 for b in marked if b["status"] == "pending_review")
    pending = sum(b["pending"] for b in marked)
    not_attempted = sum(b["marks"] for b in marked if b["status"] == "not_answered")

    return {
        "stages": breakdown,
        "max_score": max_score,
        # None rather than 0 when nothing is marked at all, so the UI can say
        # "not scored" instead of implying the student earned nothing.
        "auto_scored": (auto_scored + partial) if max_score else None,
        "teacher_scored": teacher_scored if max_score else None,
        "awarded_total": (auto_scored + teacher_scored + partial) if max_score else None,
        "pending_review": pending if max_score else None,
        "not_attempted": not_attempted if max_score else None,
        "fully_graded": bool(max_score) and pending == 0,
    }


def stages_needing_review(stages: list[dict], responses: list[dict]) -> list[dict]:
    """The stages a teacher still owes a mark on, for the marking panel.

    Includes stages the student never answered: those need a decision too --
    zero, or excused -- and leaving them out is how a student silently ends up
    with no mark at all.
    """
    return [
        b for b in score_student(stages, responses)["stages"]
        if b["status"] in ("pending_review", "not_answered")
    ]
