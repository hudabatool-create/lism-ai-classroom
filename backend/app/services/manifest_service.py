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
from collections import Counter
from typing import NamedTuple

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
        manifest["totalMarks"] = _coerce_marks(sum(s["marks"] or 0 for s in manifest["stages"]))
        return manifest

    return _unmanaged_manifest(fallback_title)


def _coerce_marks(value) -> float | None:
    """Marks, or None when the stage genuinely awards none.

    None and 0 mean different things all the way through the reports: None is
    "this stage isn't marked", 0 is "marked, scored nothing". Anything
    unparseable becomes None rather than 0, so a malformed manifest can never
    invent a zero against a student.
    """
    if value is None or value is False or value == "":
        return None
    try:
        marks = float(value)
    except (TypeError, ValueError):
        return None
    return marks if marks > 0 else None


def _normalize_criteria(raw) -> list[dict]:
    """Rubric criteria, dropping any that carry no marks."""
    criteria = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        marks = _coerce_marks(item.get("marks"))
        if marks is None:
            continue
        criteria.append({
            "label": str(item.get("label") or "Criterion"),
            "marks": marks,
            "descriptor": str(item.get("descriptor") or ""),
            # Whether the activity can score this itself. Anything not
            # explicitly objective needs a human, which is the safe default:
            # a wrong auto-mark on written work is worse than no mark.
            "objective": bool(item.get("objective", False)),
        })
    return criteria


def _normalize_stage(raw: dict, index: int) -> dict:
    marks = _coerce_marks(raw.get("marks"))
    criteria = _normalize_criteria(raw.get("rubric"))

    # The portion the activity can mark on its own. Declared value wins;
    # otherwise it is the sum of the objective rubric criteria. Never more
    # than the stage total -- the remainder is what the teacher owes.
    auto_marks = _coerce_marks(raw.get("autoMarks"))
    if auto_marks is None and criteria:
        auto_marks = _coerce_marks(sum(c["marks"] for c in criteria if c["objective"]))
    if marks is None:
        auto_marks = None
    elif auto_marks is not None:
        auto_marks = min(auto_marks, marks)

    stage_id = raw.get("id") or f"stage-{index}"
    return {
        "id": stage_id,
        "label": _clean_label(raw.get("label") or "", f"Stage {index + 1}"),
        "type": raw.get("type") or "activity",
        # An activity that declares no duration gets the framework's timing for
        # that part of the lesson, not one flat default for everything.
        "durationSeconds": int(
            raw.get("durationSeconds")
            or _STAGE_MINUTES.get(stage_id, DEFAULT_STAGE_DURATION_SECONDS // 60) * 60
        ),
        "sequentialLock": bool(raw.get("sequentialLock", True)),
        # The element this stage lives in, when we know it. Lets the student's
        # screen be pinned by name rather than by position in the document.
        "anchor": raw.get("anchor") or "",
        "marks": marks,
        "autoMarks": auto_marks,
        # Marks no machine should award: the teacher's to give, after seeing
        # the work and usually after discussing it with the class.
        "teacherMarks": None if marks is None else marks - (auto_marks or 0),
        "rubric": criteria,
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
        "totalMarks": _coerce_marks(sum(s["marks"] or 0 for s in stages)),
    }


# Sections we can recognise in an activity that carries no manifest. Matched
# against a section's data-stage/id/class and its heading text, so an activity
# authored outside LISM still gets real, teacher-paced stages instead of
# collapsing into one unnamed block.
#
# Two kinds of pattern:
#   * repeatable -- numbered sections a single activity has many of ("Card 3",
#     "Question 5"). Each match becomes its own stage, numbered in document
#     order, so an 8-card flashcard set recovers all 8 stages.
#   * single -- named once per activity. First match wins; later ones are
#     ignored so a stray mention doesn't create a phantom stage.
#
# Order matters: the numbered patterns come first because they are the most
# specific. Without that, "Exit Question 2" would be swallowed by the Exit
# Ticket pattern and every question after the first would disappear.
class _StagePattern(NamedTuple):
    id: str
    label: str
    type: str
    pattern: re.Pattern[str]
    repeatable: bool = False


def _p(id_: str, label: str, type_: str, regex: str, repeatable: bool = False) -> _StagePattern:
    return _StagePattern(id_, label, type_, re.compile(regex, re.IGNORECASE), repeatable)


_STAGE_PATTERNS: list[_StagePattern] = [
    # --- Numbered, repeating sections -------------------------------------
    _p("exit", "Exit Question", "exit-ticket", r"\bexit[\s\-_]*(?:question|ticket)?[\s\-_]*\d+\b", True),
    _p("q", "Question", "question", r"\b(?:question|q)[\s\-_]*\d+\b", True),
    _p("s", "Statement", "question", r"\bstatement[\s\-_]*\d+\b", True),
    _p("card", "Card", "card", r"\bcard[\s\-_]*\d+\b", True),
    _p("puzzle", "Lock", "puzzle", r"\b(?:puzzle|lock|clue|riddle)[\s\-_]*\d+\b", True),
    _p("round", "Round", "round", r"\bround[\s\-_]*\d+\b", True),
    _p("task", "Task", "activity", r"\b(?:task|part|challenge)[\s\-_]*\d+\b", True),
    # --- Lesson deck / worksheet framework ---------------------------------
    # "title" only as a standalone marker/word -- so a data-stage="title" or a
    # "Title Slide" heading counts, but class="card-title" does not.
    _p("title", "Title", "title", r"title[\s\-_]?slide|\bcover\b|(?:^|\s)title(?:\s|$)"),
    _p("keywords", "Keywords & Objective", "keywords", r"\bkeyword|\bvocabulary\b"),
    _p("objectives", "Learning Objectives", "objectives", r"\bobjective|success criteria|learning outcome|\bi can\b"),
    _p("starter", "Starter", "starter", r"\bstarter\b|\bretrieval\b|\bdo now\b|\bbell work\b|\bwarm[\s\-]?up\b|quick recall"),
    _p("main-teaching", "Main Teaching", "teaching", r"main teaching|\bteaching\b|knowledge box|worked example|\bi do\b|\binput\b"),
    _p("guided-practice", "Guided Practice", "practice", r"guided practice|\bwe do\b|\bpractice\b"),
    _p("main-activity", "Main Activity", "main-activity", r"main activity|main task|\byou do\b|\bindependent\b"),
    _p("rubric", "Mark Scheme", "rubric", r"\brubric\b|mark scheme|\bmarking\b"),
    _p("connection", "Connection Link", "connection", r"\buae\b|cross[\s\-]?curricular|\bconnection\b|\bai link\b"),
    _p("exit-ticket", "Exit Ticket", "exit-ticket", r"exit[\s\-]?ticket|\bexit\b"),
    # --- Simulation / coding ------------------------------------------------
    _p("scenario", "Scenario", "scenario", r"\bscenario\b|\bthe story\b|\bbriefing\b|\bstory\b"),
    _p("explore", "Explore the Variables", "explore", r"\bexplore\b|\bvariables?\b|\bcontrols?\b|\bsandbox\b"),
    _p("observation", "Observation", "observation", r"\bobservations?\b|\brecord (?:your|the) \b"),
    _p("analysis", "Analysis", "analysis", r"\banalysis\b|\banaly[sz]e\b|\bconclusion\b"),
    _p("problem", "The Problem", "problem", r"\bthe problem\b|problem statement|\bbrief\b"),
    _p("predict", "Predict the Output", "predict", r"\bpredict\b"),
    _p("debug", "Find the Bug", "debug", r"\bdebug\b|find the bug|fix the code|\bspot the error\b"),
    _p("write", "Write Your Code", "code", r"write (?:your )?code|your solution|\bcode editor\b"),
    _p("tests", "Test Cases", "tests", r"test cases?\b|\btest your\b"),
    # --- Games, puzzles, interactives ---------------------------------------
    _p("how-to-play", "How to Play", "instructions", r"how to play|\bthe rules\b|\binstructions\b"),
    _p("results", "Results", "results", r"\bresults?\b|\bleaderboard\b|final score|\byour score\b"),
    _p("escaped", "Escaped", "results", r"\bescaped\b|\byou\'?re out\b"),
    _p("across", "Across Clues", "clues", r"\bacross\b"),
    _p("down", "Down Clues", "clues", r"\bdown clues?\b"),
    _p("sort", "Sort Them", "sort", r"\bsort\b|\bcategori[sz]e\b|\bdrag (?:them|the)\b"),
    _p("sequence", "Put Them In Order", "sequence", r"\bsequence\b|put them in order|\bin order\b|\btimeline\b"),
    # Deliberately not a bare "pair" -- that would swallow "Explain a Pair",
    # which is its own stage in the matching activity.
    _p("match", "Match the Pairs", "match", r"\bmatch(?:ing)?\b|pair them"),
    # --- Thinking, discussion, closing --------------------------------------
    _p("prompt", "The Big Question", "prompt", r"big question|\bbrainstorm\b|\bthe question\b"),
    _p("ideas", "Post Your Ideas", "ideas", r"your ideas|\badd (?:an )?idea|post (?:your|an) \b"),
    _p("group", "Group the Ideas", "group", r"group the|\bgrouping\b|\bthemes\b|\bcluster\b"),
    _p("best", "Choose the Strongest", "evaluate", r"\bstrongest\b|best idea|\bchoose the\b|\bvote\b"),
    _p("poll", "Class Poll", "poll", r"\bpoll\b"),
    _p("confidence", "Confidence Check", "confidence", r"\bconfidence\b"),
    _p("self-check", "Self Check", "self-check", r"self[\s\-]?check|\bhow did you do\b"),
    _p("apply", "Apply It", "apply", r"\bapply it\b|\bapplication\b"),
    _p("misconception", "Spot the Mistake", "misconception", r"\bmisconception\b|spot the mistake|what\'?s wrong"),
    _p("justify", "Justify Your Choice", "justify", r"\bjustif"),
    _p("explain", "Explain", "explain", r"\bexplain\b"),
    _p("review", "Review", "review", r"\breview\b"),
    _p("reflection", "Reflection", "reflection", r"\breflection\b|\breflect\b|3-2-1|self[\s\-]?assessment"),
]

_SECTION_RE = re.compile(
    r'<(section|div|article)\b([^>]*)>(.*?)</\1>', re.DOTALL | re.IGNORECASE
)
_HEADING_RE = re.compile(r"<h[1-4][^>]*>(.*?)</h[1-4]>", re.DOTALL | re.IGNORECASE)
_TAGS_RE = re.compile(r"<[^>]+>")
_ATTR_RE = re.compile(r'(?:data-stage|id|class)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
# The section's own handle in the document, which is how the student's screen
# is pinned to exactly the right section rather than counting positions.
_ANCHOR_RE = re.compile(r'data-stage\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
_ID_RE = re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
_CLASS_RE = re.compile(r'\bclass\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)


class _Block(NamedTuple):
    """One candidate section, before we decide whether it becomes a stage."""

    tag: str
    markers: str
    classes: frozenset[str]
    anchor: str
    heading: str
    inner: str
    entry: _StagePattern | None


def _match_stage(*texts: str) -> _StagePattern | None:
    haystack = " ".join(t for t in texts if t)
    for entry in _STAGE_PATTERNS:
        if entry.pattern.search(haystack):
            return entry
    return None


# How long each part of a LISM lesson is meant to take. Used only when the
# activity did not declare its own durations -- giving every recovered stage
# the same five minutes made a 50-minute lesson look like a stopwatch drill
# and told the teacher nothing about the pacing the lesson was written for.
_STAGE_MINUTES = {
    "title": 1, "keywords": 2, "objectives": 2,
    "starter": 5, "main-teaching": 10, "guided-practice": 5,
    "main-activity": 10, "rubric": 2, "connection": 3,
    "exit-ticket": 5, "reflection": 2,
    "scenario": 3, "explore": 5, "observation": 4, "analysis": 5,
    "problem": 3, "predict": 3, "debug": 5, "write": 8, "tests": 3,
    "how-to-play": 2, "results": 3, "review": 3, "match": 5, "sort": 4,
}
_DEFAULT_STAGE_MINUTES = 5

# "Recommended Duration: 5 minutes", "(3 min)", "10 minutes + feedback"
_DURATION_RE = re.compile(r"(\d{1,3})\s*(?:minutes?|mins?\b|m\b)", re.IGNORECASE)


def _recovered_duration(stage_id: str, section_html: str) -> int:
    """Seconds for a stage the activity didn't time itself.

    Prefers what the lesson says out loud -- decks built from the LISM prompt
    print "Recommended Duration: 5 minutes" beside the slide title -- and
    otherwise falls back to the framework's own shape rather than one flat
    number for everything.
    """
    text = _TAGS_RE.sub(" ", section_html)[:600]
    match = _DURATION_RE.search(text)
    if match:
        minutes = int(match.group(1))
        if 1 <= minutes <= 60:
            return minutes * 60
    return _STAGE_MINUTES.get(stage_id, _DEFAULT_STAGE_MINUTES) * 60


# An AI that writes its manifest with a template literal leaves the
# placeholder behind verbatim -- "${data.d1.title}" is a real label we have
# seen. Showing that to a teacher is worse than showing nothing.
_PLACEHOLDER_RE = re.compile(r"\$\{[^}]*\}|\{\{[^}]*\}\}|\[[A-Z][A-Z _-]{2,}\]")


def _clean_label(label: str, fallback: str) -> str:
    cleaned = _PLACEHOLDER_RE.sub("", label or "").strip(" .-–—:·")
    return " ".join(cleaned.split()) or fallback


def infer_stages_from_html(html: str) -> list[dict]:
    """Best-effort lesson stages for HTML with no manifest.

    An activity written by pasting a master prompt into an AI elsewhere and
    then uploaded here has no manifest block, and without this it collapses
    into a single unnamed stage -- no stage list, no teacher pacing, nothing
    for Preview's Prev/Next to step through. Recognising the lesson's own
    sections restores all of that without the teacher regenerating anything.

    Conservative on purpose: only sections whose marker or heading clearly
    name a known stage count, named stages are taken once, and document order
    is preserved. Returns [] when nothing recognisable is found, so the caller
    keeps the honest single-stage fallback.
    """
    blocks: list[_Block] = []
    for tag, attrs, inner in _SECTION_RE.findall(html):
        markers = " ".join(_ATTR_RE.findall(attrs))
        heading_html = _HEADING_RE.search(inner)
        heading = _TAGS_RE.sub(" ", heading_html.group(1)) if heading_html else ""
        class_match = _CLASS_RE.search(attrs)
        anchor_match = _ANCHOR_RE.search(attrs) or _ID_RE.search(attrs)
        blocks.append(
            _Block(
                tag=tag.lower(),
                markers=markers,
                classes=frozenset((class_match.group(1) if class_match else "").split()),
                anchor=anchor_match.group(1) if anchor_match else "",
                heading=heading,
                inner=inner,
                entry=_match_stage(markers, heading),
            )
        )

    # A section we don't recognise is still a section.
    #
    # Recovery used to keep only sections whose heading matched a known name,
    # and drop the rest without a word. A worksheet opening with "Section 1 -
    # Worksheet Details" lost that section entirely: students never saw it, and
    # worse, the stage list no longer lined up with the document, so the class
    # ran a whole lesson one section behind -- the teacher started Section 4 on
    # a ten-minute clock while every student sat looking at the Starter.
    #
    # So once an activity has shown us what its sections look like, take its
    # unrecognised siblings too. A peer is the same tag, carrying the same
    # class the recognised sections share, and headed like them. That is
    # specific enough to exclude layout wrappers -- which have no heading --
    # while never again silently losing part of a lesson.
    recognised = [b for b in blocks if b.entry]
    peer_tag = recognised[0].tag if recognised else ""
    class_counts: Counter[str] = Counter(c for b in recognised for c in b.classes)
    peer_classes = {c for c, n in class_counts.items() if n >= 2}

    def is_peer(block: _Block) -> bool:
        return (
            block.entry is None
            and bool(peer_classes)
            and block.tag == peer_tag
            and bool(block.classes & peer_classes)
            and bool(block.heading.strip())
        )

    found: list[dict] = []
    seen_single: set[str] = set()
    counters: dict[str, int] = {}
    seen_signatures: set[str] = set()
    used_ids: set[str] = set()

    for position, block in enumerate(blocks):
        entry, inner, markers = block.entry, block.inner, block.markers
        if not entry and not is_peer(block):
            continue

        # Prefer the activity's own heading -- "Starter / Retrieval" is more
        # useful to the teacher than our generic label.
        # Unescape so a heading reads "Keywords & Objective" on the teacher's
        # stage list, not "Keywords &amp; Objective".
        clean_heading = _clean_label(html_lib.unescape(block.heading), "")[:60]

        if entry is None:
            # An unrecognised peer: named by its own heading, timed by whatever
            # it says out loud, and worth no marks we would have to invent.
            stage_id = block.anchor or f"section-{position}"
            if stage_id in used_ids:
                continue
            used_ids.add(stage_id)
            found.append(
                {
                    "id": stage_id,
                    "label": clean_heading or f"Section {len(found) + 1}",
                    "type": "section",
                    "durationSeconds": _recovered_duration(stage_id, inner),
                    "sequentialLock": True,
                    "marks": None,
                    "anchor": block.anchor,
                }
            )
            continue

        if entry.repeatable:
            # Nested markup can surface the same block twice (an outer section
            # and the inner div that carries the marker). Two genuinely
            # different cards never share a heading and marker set, so
            # collapsing on that keeps "Card 3" from becoming two stages.
            signature = f"{entry.id}|{clean_heading.lower()}|{markers.lower()}"
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            counters[entry.id] = counters.get(entry.id, 0) + 1
            number = counters[entry.id]
            stage_id = f"{entry.id}-{number}"
            label = clean_heading or f"{entry.label} {number}"
        else:
            if entry.id in seen_single:
                continue
            seen_single.add(entry.id)
            stage_id = entry.id
            label = clean_heading or entry.label

        used_ids.add(stage_id)
        found.append(
            {
                "id": stage_id,
                "label": label,
                "type": entry.type,
                "durationSeconds": _recovered_duration(stage_id, inner),
                "sequentialLock": True,
                "marks": 10 if stage_id == "main-activity" else None,
                # Which element in the document this stage is. Carried so the
                # student's screen can be pinned to the right section by name
                # instead of by counting -- counting is what broke a whole
                # lesson the moment one section was not recognised.
                "anchor": block.anchor,
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
        # Arbitrary HTML declares no marks, and we will not invent any.
        "totalMarks": None,
    }
