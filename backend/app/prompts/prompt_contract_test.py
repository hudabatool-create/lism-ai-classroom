"""The contract the master prompt demands must be the contract LISM reads.

Run:  python app/prompts/prompt_contract_test.py   (from backend/)

Everything checked here is lifted out of the prompt text itself rather than
copied into this file, so the two cannot drift apart silently. They already did
once: rule 3's reporting snippet was written with `stage:` and `question:`
while the student player reads `stageId` and the integration spec below it
documents `questionId`. A worked example that contradicts its own spec is worse
than no example at all, because a model will copy it faithfully.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(HERE, "..", "..")
PROMPT = os.path.join(HERE, "lesson_deck_master_prompt.txt")
PLAYER = os.path.join(BACKEND, "..", "frontend", "src", "app", "join", "[code]", "page.tsx")
sys.path.insert(0, BACKEND)

from app.services.manifest_service import (  # noqa: E402
    _STAGE_PATTERNS, extract_manifest)

prompt = io.open(PROMPT, encoding="utf-8").read()
results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}")
    if detail:
        print(f"      {detail}")


# --- the manifest example must be valid JSON and give LISM the right split ---
block = re.search(r'(\{\s*\n\s*"id": "main-activity".*?\n  \})', prompt, re.S)
check("the manifest example is still in the prompt", block is not None)
if not block:
    sys.exit(1)

try:
    stage = json.loads(block.group(1))
    parsed = True
except json.JSONDecodeError as exc:
    stage, parsed = {}, False
    print(f"      {exc}")
check("the manifest example the prompt shows is valid JSON", parsed)

html = (
    '<html><head><script type="application/json" id="lism-manifest">'
    + json.dumps({"lessonType": "lesson-deck", "stages": [stage]})
    + '</script></head><body>'
      '<section class="slide" data-stage="main-activity"><h2>Main Activity</h2></section>'
      '</body></html>'
)
s = extract_manifest(html, fallback_title="T")["stages"][0]

check("the stage keeps its id", s["id"] == "main-activity", s["id"])
check("the stage is anchored to its own element", s["anchor"] == "main-activity", repr(s["anchor"]))
check("the Main Activity is worth 10", s["marks"] == 10, str(s["marks"]))
check("LISM knows what the activity can mark itself (DOK 1 + DOK 2 = 5)",
      s["autoMarks"] == 5, str(s["autoMarks"]))
check("LISM knows what the teacher still owes (DOK 3 + DOK 4 = 5)",
      s["teacherMarks"] == 5, str(s["teacherMarks"]))
check("all four DOK criteria survive", len(s["rubric"]) == 4, str(len(s["rubric"])))
for c in s["rubric"]:
    who = "the activity" if c["objective"] else "the TEACHER"
    print(f"      {c['label']:<18} {c['marks']:>4} marks -> {who}")

# --- the reporting snippet must name the fields the player reads -------------
snippet = re.search(r"function reportToLISM\(.*?\n      \}", prompt, re.S)
check("rule 3's reporting snippet is still in the prompt", snippet is not None)
if snippet:
    body = snippet.group(0)
    for field in ("stageId", "questionId", "correct", "answer", "mark", "maxMark", "dok"):
        check(f"the snippet sends `{field}`", f"{field}:" in body)

player = io.open(PLAYER, encoding="utf-8").read()
check("the student player reads `data.stageId`", "data.stageId" in player)
check("the student player reads `data.answer`", "data.answer" in player)
check("the student player reads `data.mark`", "data.mark" in player)

# --- every id in the fixed stage table must be one LISM also recognises -----
#
# The table is what a compliant deck writes into data-stage. Recovery is the
# fallback for decks that carry no manifest. If the two vocabularies disagree,
# a compliant deck and a recovered one get different stage names for the same
# lesson, and the teacher's stage list changes depending on which AI wrote it.
known = {e.id for e in _STAGE_PATTERNS} | {"title"}
table = re.findall(r"^  \d+\s+([a-z-]+)\s{2,}\S", prompt, re.M)
unknown = sorted(set(table) - known)
check("the fixed stage table has 11 rows", len(table) == 11, str(len(table)))
check("every fixed stage id is one LISM recognises", not unknown, str(unknown))

passed = sum(results)
print(f"\nTOTAL {passed} passed, {len(results) - passed} failed")
sys.exit(0 if all(results) else 1)
