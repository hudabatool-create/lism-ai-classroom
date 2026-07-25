"""Extracts and validates the LISM Lesson Manifest embedded in an activity's HTML.

Generated/uploaded activities may include an inert, parseable manifest block:

    <script type="application/json" id="lism-manifest">{...}</script>

Activities without one (a teacher's own arbitrary HTML upload, or an older
activity from before the Classroom Engine existed) degrade gracefully into a
single-stage "unmanaged" manifest so they keep launching and working exactly
as they did before — the engine treats them as one unmanaged stage rather
than rejecting them.
"""

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
