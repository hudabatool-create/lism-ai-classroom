"""AI Insights: class summary, misconceptions, and recommendations built from
real session data. Always computes genuine statistics first; only the
narrative wrapping around them is AI-generated, and only when an OpenAI key
is configured. Without one, the statistics are returned with a plain
rule-based narrative -- clearly labeled, never presented as if an AI wrote it.
"""

import json
from collections import Counter

from app.core.config import settings


def _compute_stats(activity: dict, students: list[dict], responses: list[dict], focus_violations: list[dict]) -> dict:
    stages = activity["manifest"]["stages"]
    joined = len(students)
    responded_student_ids = {r["student_id"] for r in responses}
    participation_rate = round(100 * len(responded_student_ids) / joined) if joined else 0

    graded = [r for r in responses if r["correct"] is not None]
    correct_count = sum(1 for r in graded if r["correct"])
    correct_rate = round(100 * correct_count / len(graded)) if graded else None

    per_stage = []
    for stage in stages:
        stage_responses = [r for r in responses if r["stage_id"] == stage["id"]]
        stage_graded = [r for r in stage_responses if r["correct"] is not None]
        wrong_answers = [r["answer"] for r in stage_graded if r["correct"] is False and r["answer"]]
        most_common_wrong = Counter(wrong_answers).most_common(1)
        per_stage.append(
            {
                "stage_id": stage["id"],
                "label": stage["label"],
                "responses": len(stage_responses),
                "correct": sum(1 for r in stage_graded if r["correct"]),
                "incorrect": sum(1 for r in stage_graded if not r["correct"]),
                "completion_rate": round(100 * len(stage_responses) / joined) if joined else 0,
                "most_common_wrong_answer": most_common_wrong[0][0] if most_common_wrong else None,
                "most_common_wrong_count": most_common_wrong[0][1] if most_common_wrong else 0,
            }
        )

    violation_counts = Counter(v["student_id"] for v in focus_violations)
    locked_count = sum(1 for sid in violation_counts if violation_counts[sid] >= 3)

    student_stats = []
    for s in students:
        s_responses = [r for r in responses if r["student_id"] == s["id"]]
        s_graded = [r for r in s_responses if r["correct"] is not None]
        student_stats.append(
            {
                "student_id": s["id"],
                "name": s["name"],
                "responses": len(s_responses),
                "correct": sum(1 for r in s_graded if r["correct"]),
                "graded": len(s_graded),
                "needs_help": s.get("needs_help", False),
                "help_requests": s.get("help_requests", 0),
                "coach_messages": s.get("coach_messages", 0),
                "violations": violation_counts.get(s["id"], 0),
                "locked": violation_counts.get(s["id"], 0) >= 3,
            }
        )

    return {
        "students_joined": joined,
        "participation_rate": participation_rate,
        "correct_rate": correct_rate,
        "per_stage": per_stage,
        "focus_violation_total": len(focus_violations),
        "students_locked": locked_count,
        "student_stats": student_stats,
    }


def _canned_narrative(activity: dict, stats: dict) -> dict:
    topic = activity["manifest"].get("topic") or activity["title"]

    summary_parts = [
        f"{stats['participation_rate']}% of students ({len(stats['student_stats'])} joined) submitted at least one response."
    ]
    if stats["correct_rate"] is not None:
        summary_parts.append(f"Overall correct-answer rate across scored questions: {stats['correct_rate']}%.")
    class_summary = " ".join(summary_parts)

    misconceptions = [
        f"In \"{stage['label']}\", the most common incorrect answer was \"{stage['most_common_wrong_answer']}\" "
        f"({stage['most_common_wrong_count']} student(s))."
        for stage in stats["per_stage"]
        if stage["most_common_wrong_answer"]
    ]
    if not misconceptions:
        misconceptions = ["No incorrect responses recorded yet — not enough data to identify a common misconception."]

    recommendations = []
    if stats["correct_rate"] is not None and stats["correct_rate"] < 70:
        recommendations.append(f"Consider a short re-teach of \"{topic}\" before moving to the next lesson.")
    elif stats["correct_rate"] is not None:
        recommendations.append(f"Understanding of \"{topic}\" looks solid — consider an extension task for this class.")
    if stats["students_locked"] > 0:
        recommendations.append(
            f"{stats['students_locked']} student(s) were locked out for repeated focus violations — follow up individually."
        )
    if any(s["coach_messages"] >= 4 for s in stats["student_stats"]):
        recommendations.append(
            "Some students asked the AI Coach for help repeatedly without resolving it — worth a quick 1:1 check-in."
        )
    if not recommendations:
        recommendations.append("Not enough response data yet for a specific recommendation.")

    student_notes = []
    for s in stats["student_stats"]:
        bits = [f"{s['responses']} response(s)"]
        if s["graded"]:
            bits.append(f"{s['correct']}/{s['graded']} correct")
        if s["locked"]:
            bits.append("locked (focus violations)")
        elif s["needs_help"]:
            bits.append("flagged needs help")
        student_notes.append({"name": s["name"], "note": ", ".join(bits)})

    return {
        "class_summary": class_summary,
        "misconceptions": misconceptions,
        "recommendations": recommendations,
        "student_notes": student_notes,
    }


def _narrative_with_openai(activity: dict, stats: dict) -> dict | None:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        manifest = activity["manifest"]
        prompt = (
            "You are an assistant helping a teacher understand how their class did on a lesson. "
            "Based on the statistics below (already computed -- do not invent numbers), write teacher-facing "
            "insights. Return ONLY a JSON object with keys: class_summary (2-3 sentences), "
            "misconceptions (array of short strings), recommendations (array of short strings), "
            "student_notes (array of {name, note} with one short note per student, referencing their own stats only).\n\n"
            f"Lesson: {manifest.get('topic')} ({manifest.get('subject')}, Grade {manifest.get('grade')})\n"
            f"Statistics JSON: {json.dumps(stats)}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        content = (resp.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content[:4].lower() == "json":
                content = content[4:]
        parsed = json.loads(content)
        if not all(k in parsed for k in ("class_summary", "misconceptions", "recommendations", "student_notes")):
            return None
        return parsed
    except Exception:
        return None


def build_insights(activity: dict, students: list[dict], responses: list[dict], focus_violations: list[dict]) -> dict:
    stats = _compute_stats(activity, students, responses, focus_violations)
    if settings.openai_api_key:
        narrative = _narrative_with_openai(activity, stats)
        if narrative:
            return {"source": "ai", "stats": stats, **narrative}
    return {"source": "statistical", "stats": stats, **_canned_narrative(activity, stats)}
