"""Extracts and validates the LISM Lesson Manifest embedded in an activity's HTML.

Generated/uploaded activities may include an inert, parseable manifest block:

    <script type="application/json" id="lism-manifest">{...}</script>

Activities without one (a teacher's own arbitrary HTML upload, or an older
activity from before the Classroom Engine existed) degrade gracefully into a
single-stage "unmanaged" manifest so they keep launching and working exactly
as they did before — the engine treats them as one unmanaged stage rather
than rejecting them.
"""

import html as html_lib
import json
import re

MANIFEST_PATTERN = re.compile(
    r'<script[^>]*id=["\']lism-manifest["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)

DEFAULT_STAGE_DURATION_SECONDS = 600


def extract_manifest(html: str, *, fallback_title: str = "") -> dict:
    match = MANIFEST_PATTERN.search(html)
    if match:
        try:
            raw = json.loads(match.group(1))
            return _normalize_manifest(raw)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # No manifest (or an unparseable one): try to recognise the lesson's own
    # sections before giving up on pacing entirely.
    inferred = infer_stages_from_html(html)
    if inferred:
        manifest = _unmanaged_manifest(fallback_title)
        manifest["stages"] = [_normalize_stage(s, i) for i, s in enumerate(inferred)]
        # Stages were recovered rather than declared, so the teacher can pace
        # it -- but flag how we got them, since ids are guesses and an
        # activity that ignores stage commands still won't hide its sections.
        manifest["managed"] = True
        manifest["stagesInferred"] = True
        return manifest

    return _unmanaged_manifest(fallback_title)


def _normalize_stage(raw: dict, index: int) -> dict:
    return {
        "id": raw.get("id") or f"stage-{index}",
        "label": raw.get("label") or f"Stage {index + 1}",
        "type": raw.get("type") or "activity",
        "durationSeconds": int(raw.get("durationSeconds") or DEFAULT_STAGE_DURATION_SECONDS),
        "sequentialLock": bool(raw.get("sequentialLock", True)),
        "marks": raw.get("marks"),
    }


def _normalize_manifest(raw: dict) -> dict:
    stages_raw = raw.get("stages") or []
    stages = [_normalize_stage(s, i) for i, s in enumerate(stages_raw)] or [_normalize_stage({}, 0)]
    return {
        "managed": True,
        "lessonType": raw.get("lessonType", "activity"),
        "subject": raw.get("subject", ""),
        "grade": raw.get("grade", ""),
        "week": raw.get("week", ""),
        "topic": raw.get("topic", ""),
        "learningObjectives": raw.get("learningObjectives", {}),
        "keywords": raw.get("keywords", []),
        "dok": raw.get("dok", []),
        "deliveryMode": raw.get("deliveryMode", "lesson"),
        "sessionType": raw.get("sessionType", "lesson"),
        "stages": stages,
    }


# Lesson sections we can recognise in an activity that carries no manifest.
# Matched against a section's data-stage/id/class and its heading text, so a
# deck or worksheet authored outside LISM still gets real, teacher-paced
# stages instead of collapsing into one unnamed block.
_STAGE_PATTERNS: list[tuple[str, str, str, tuple[str, ...]]] = [
    # (stage id, label, type, phrases that identify it)
    ("title", "Title", "title", ("title-slide", "cover")),
    ("keywords", "Keywords & Objective", "keywords", ("keyword", "vocabulary")),
    ("objectives", "Learning Objectives", "objectives", ("objective", "success criteria", "learning outcome", "i can")),
    ("starter", "Starter", "starter", ("starter", "retrieval", "do now", "bell work", "warm up", "warm-up")),
    ("main-teaching", "Main Teaching", "teaching", ("main teaching", "teaching", "knowledge box", "worked example", "i do", "input")),
    ("guided-practice", "Guided Practice", "practice", ("guided practice", "we do", "practice")),
    ("main-activity", "Main Activity", "main-activity", ("main activity", "main task", "you do", "independent")),
    ("rubric", "Mark Scheme", "rubric", ("rubric", "mark scheme", "marking")),
    ("connection", "Connection Link", "connection", ("uae", "cross-curricular", "cross curricular", "connection", "ai link")),
    ("exit-ticket", "Exit Ticket", "exit-ticket", ("exit ticket", "exit-ticket", "exit")),
    ("reflection", "Reflection", "reflection", ("reflection", "reflect", "3-2-1", "self-assessment")),
]

_SECTION_RE = re.compile(
    r'<(section|div|article)\b([^>]*)>(.*?)</\1>', re.DOTALL | re.IGNORECASE
)
_HEADING_RE = re.compile(r"<h[1-4][^>]*>(.*?)</h[1-4]>", re.DOTALL | re.IGNORECASE)
_TAGS_RE = re.compile(r"<[^>]+>")
_ATTR_RE = re.compile(r'(?:data-stage|id|class)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)


def _match_stage(*texts: str) -> tuple[str, str, str] | None:
    haystack = " ".join(t.lower() for t in texts if t)
    for stage_id, label, stage_type, phrases in _STAGE_PATTERNS:
        if any(p in haystack for p in phrases):
            return stage_id, label, stage_type
    return None


def infer_stages_from_html(html: str) -> list[dict]:
    """Best-effort lesson stages for HTML with no manifest.

    An activity written by pasting a master prompt into an AI elsewhere and
    then uploaded here has no manifest block, and without this it collapses
    into a single unnamed stage -- no stage list, no teacher pacing, nothing
    for Preview's Prev/Next to step through. Recognising the lesson's own
    sections restores all of that without the teacher regenerating anything.

    Conservative on purpose: only sections whose marker or heading clearly
    names a known lesson stage count, each stage is taken once, and document
    order is preserved. Returns [] when nothing recognisable is found, so the
    caller keeps the honest single-stage fallback.
    """
    found: list[dict] = []
    seen: set[str] = set()

    for _tag, attrs, inner in _SECTION_RE.findall(html):
        markers = " ".join(_ATTR_RE.findall(attrs))
        heading_html = _HEADING_RE.search(inner)
        heading = _TAGS_RE.sub(" ", heading_html.group(1)) if heading_html else ""
        match = _match_stage(markers, heading)
        if not match:
            continue
        stage_id, label, stage_type = match
        if stage_id in seen:
            continue
        seen.add(stage_id)
        # Prefer the activity's own heading -- "Starter / Retrieval" is more
        # useful to the teacher than our generic label.
        # Unescape so a heading reads "Keywords & Objective" on the teacher's
        # stage list, not "Keywords &amp; Objective".
        clean_heading = " ".join(html_lib.unescape(heading).split())[:60]
        found.append(
            {
                "id": stage_id,
                "label": clean_heading or label,
                "type": stage_type,
                "durationSeconds": 300,
                "sequentialLock": True,
                "marks": 10 if stage_id == "main-activity" else None,
            }
        )

    # One recognised section isn't a paced lesson -- don't dress it up as one.
    return found if len(found) >= 2 else []


def _unmanaged_manifest(title: str) -> dict:
    return {
        "managed": False,
        "lessonType": "standalone",
        "subject": "",
        "grade": "",
        "week": "",
        "topic": title,
        "learningObjectives": {},
        "keywords": [],
        "dok": [],
        "deliveryMode": "lesson",
        "sessionType": "lesson",
        "stages": [_normalize_stage({"id": "main", "label": title or "Activity", "type": "standalone"}, 0)],
    }
