"""Checks for recovering stages from an activity that carries no manifest.

Run from the backend directory:

    python app/services/manifest_service_test.py

Standalone rather than pytest, matching frontend/src/lib/lockstep.test.mjs --
these two files cover the two halves of the same feature, and both need to be
runnable without installing anything.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from app.services.manifest_service import (  # noqa: E402
    _match_stage, extract_manifest, infer_stages_from_html)

results: list[bool] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}")
    if detail:
        print(f"      {detail}")


# ---------------------------------------------------------------------------
# The worksheet shape that ran a real class a section behind.
#
# Section 1 matched no known stage name, so it was dropped. That left nine
# stages describing a ten-section document, and because the student's screen
# was pinned by counting position, every stage after it pointed one section
# too early: the teacher started Section 4 on a ten-minute clock while the
# class sat looking at the Starter.
# ---------------------------------------------------------------------------
def section(sec_id: str, title: str, minutes: str, extra_class: str = "") -> str:
    return f"""
  <section class="card {extra_class}" id="{sec_id}">
    <div class="section-header">
      <h2 class="section-title">{title}</h2>
      <span class="duration-badge">Recommended Duration: {minutes}</span>
    </div>
    <p>Body text for {title}.</p>
  </section>"""


WORKSHEET = f"""<!DOCTYPE html><html><body>
<div class="container">
  <header class="sticky-header">
    <div class="header-content"><div class="header-top">
      <div class="header-title">Grade 9 CS</div>
    </div></div>
  </header>
{section("sec-1", "Section 1 &middot; Worksheet Details", "2 minutes")}
{section("sec-2", "Section 2 &middot; Keywords &amp; Objectives", "2 minutes")}
{section("sec-3", "Section 3 &middot; Starter / Retrieval", "5 minutes", "starter-card")}
{section("sec-4", "Section 4 &middot; Knowledge Box", "10 minutes")}
{section("sec-5", "Section 5 &middot; Guided Practice", "5 minutes")}
{section("sec-6", "Section 6 &middot; Main Task (10 Marks)", "10 minutes", "main-card")}
{section("sec-7", "Section 7 &middot; UAE Connection", "3 minutes", "uae-card")}
{section("sec-8", "Section 8 &middot; Exit Ticket", "5 minutes", "exit-card")}
{section("sec-9", "Section 9 &middot; Summary &amp; Graded Rubric", "Automatic Evaluation")}
{section("sec-10", "Section 10 &middot; Student Reflection", "5 minutes")}
</div></body></html>"""

stages = infer_stages_from_html(WORKSHEET)
ids = [s["id"] for s in stages]
anchors = [s.get("anchor") for s in stages]
expected = [f"sec-{n}" for n in range(1, 11)]

check("every section becomes a stage", len(stages) == 10, f"got {len(stages)}: {ids}")
check("the unrecognised opening section is kept",
      any(a == "sec-1" for a in anchors), f"anchors: {anchors}")
check("stages are pinned to their own sections, in order",
      anchors == expected, f"anchors: {anchors}")
check("the unrecognised section is named by its own heading",
      stages[0]["label"].endswith("Worksheet Details"), stages[0]["label"])

minutes = [s["durationSeconds"] // 60 for s in stages]
check("each stage gets the duration its own section declares",
      minutes == [2, 2, 5, 10, 5, 10, 3, 5, 2, 5], f"minutes: {minutes}")

starter = next(s for s in stages if s.get("anchor") == "sec-3")
check("the Starter is five minutes, not the next section's ten",
      starter["durationSeconds"] == 300, f'{starter["durationSeconds"]}s')

# The failure this whole change exists to prevent: what the student is shown
# when the screen is pinned by counting rather than by name.
misaligned = [i for i, s in enumerate(stages) if s.get("anchor") != expected[i]]
check("counting position and naming the section now agree",
      not misaligned, f"stages off by position: {misaligned}")

check("layout wrappers do not become stages",
      not any("container" in (s.get("anchor") or "") for s in stages), f"{anchors}")
check("no stage is marked without the activity saying so",
      all(s["marks"] is None for s in stages if s.get("anchor") != "sec-6"))

# ---------------------------------------------------------------------------
# Regressions: the shapes that already worked must keep working.
# ---------------------------------------------------------------------------
DECK = """<html><body>
<section data-stage="starter" class="slide"><h2>Starter</h2><p>Recommended Duration: 5 minutes</p></section>
<section data-stage="main-activity" class="slide"><h2>Main Task</h2><p>Recommended Duration: 10 minutes</p></section>
<section data-stage="exit-ticket" class="slide"><h2>Exit Ticket</h2><p>Recommended Duration: 5 minutes</p></section>
</body></html>"""

deck = infer_stages_from_html(DECK)
check("a deck with data-stage still recovers", len(deck) == 3, f"{[s['id'] for s in deck]}")
check("data-stage is used as the anchor",
      [s.get("anchor") for s in deck] == ["starter", "main-activity", "exit-ticket"],
      f"{[s.get('anchor') for s in deck]}")

# ---------------------------------------------------------------------------
# The Progress Check: the hinge question between teaching and working alone.
#
# It has to be recognised by the several names a lesson might give it, without
# swallowing the other stages whose headings also contain "check" -- Self Check
# closes a lesson, and Fact-Check the AI is its own activity.
# ---------------------------------------------------------------------------
CHECKS = """<html><body>
<section class="slide"><h2>Section 5 &middot; Main Teaching</h2><p>Recommended Duration: 10 minutes</p></section>
<section class="slide"><h2>Section 6 &middot; Progress Check</h2><p>Recommended Duration: 2 minutes</p></section>
<section class="slide"><h2>Section 7 &middot; Main Task</h2><p>Recommended Duration: 10 minutes</p></section>
<section class="slide"><h2>Section 8 &middot; Self Check</h2><p>Recommended Duration: 3 minutes</p></section>
</body></html>"""

checks = infer_stages_from_html(CHECKS)
ids_found = [s["id"] for s in checks]
check("the Progress Check is recovered", "progress-check" in ids_found, str(ids_found))
check("it does not swallow Self Check", "self-check" in ids_found, str(ids_found))
check("teaching and main task are still their own stages",
      "main-teaching" in ids_found and "main-activity" in ids_found, str(ids_found))
check("stages stay in document order",
      ids_found == ["main-teaching", "progress-check", "main-activity", "self-check"],
      str(ids_found))

pc = next(s for s in checks if s["id"] == "progress-check")
check("the Progress Check takes its declared 2 minutes",
      pc["durationSeconds"] == 120, f'{pc["durationSeconds"]}s')
check("the Progress Check carries no marks",
      pc["marks"] is None,
      "a mark here makes guessing safer than admitting confusion")

# Other names a teacher's deck might use for the same thing.
for heading, expect in (("Quick Check", True), ("Check for Understanding", True),
                        ("Hinge Question", True), ("Mini-Check", True)):
    html = ("<html><body>"
            f"<section class='slide'><h2>Starter</h2></section>"
            f"<section class='slide'><h2>{heading}</h2></section>"
            f"<section class='slide'><h2>Exit Ticket</h2></section>"
            "</body></html>")
    got = [s["id"] for s in infer_stages_from_html(html)]
    check(f'"{heading}" is recognised as the progress check',
          ("progress-check" in got) == expect, str(got))

# ---------------------------------------------------------------------------
# Two ways a real deck lost slides, both found in an uploaded Grade 9 lesson.
# ---------------------------------------------------------------------------

# 1. Slides inside a wrapper div. A regex closing on the FIRST </div> swallowed
#    the opening slide into the wrapper's match, so the title slide was never
#    seen as a section at all.
WRAPPED = """<html><body>
<div class="deck">
  <div class="slides">
    <section class="slide active"><div class="center"><h1>Python Data Types</h1></div></section>
    <section class="slide"><h2>Starter</h2><p>Recommended: 5 min</p></section>
    <section class="slide"><h2>Main Teaching</h2><p>Recommended: 10 min</p></section>
    <section class="slide"><h2>Exit Ticket</h2><p>Recommended: 5 min</p></section>
  </div>
</div>
<div class="nav"><button>Next</button></div>
</body></html>"""

wrapped = infer_stages_from_html(WRAPPED)
labels = [s["label"] for s in wrapped]
check("slides inside a wrapper div are all found", len(wrapped) == 4,
      f"got {len(wrapped)}: {labels}")
check("the opening slide is not swallowed by the wrapper",
      any("Python Data Types" in l for l in labels), str(labels))
check("the page wrapper itself never becomes a stage",
      not any(l.strip() in ("", "deck", "slides") for l in labels), str(labels))

# 2. A rubric slide headed "Rubric - Main Activity /10" matches main-activity
#    first. With that id already taken by the real Main Activity, the block was
#    skipped entirely and the slide disappeared.
COLLIDE = """<html><body><div class="deck">
  <section class="slide"><h2>Main Activity</h2><p>Recommended: 10 min</p></section>
  <section class="slide"><h2>Rubric &mdash; Main Activity /10</h2></section>
  <section class="slide"><h2>Exit Ticket</h2><p>Recommended: 5 min</p></section>
</div></body></html>"""

collide = infer_stages_from_html(COLLIDE)
got = [s["id"] for s in collide]
check("a colliding heading falls through to its own pattern",
      got == ["main-activity", "rubric", "exit-ticket"], str(got))
check("no slide is lost to the collision", len(collide) == 3, f"{len(collide)}")

NOTHING = "<html><body><div class='wrap'><p>Just a page.</p></div></body></html>"
check("an activity with no sections stays a single unmanaged stage",
      infer_stages_from_html(NOTHING) == [], "must not invent stages")

DECLARED = """<html><head><script type="application/json" id="lism-manifest">
{"stages":[{"id":"s1","label":"One","durationSeconds":120},
           {"id":"s2","label":"Two","durationSeconds":300}]}
</script></head><body><section id="s1">A</section><section id="s2">B</section></body></html>"""
declared = extract_manifest(DECLARED, fallback_title="T")
check("a declared manifest is still preferred over recovery",
      [s["id"] for s in declared["stages"]] == ["s1", "s2"])
check("declared stages carry an anchor field",
      all("anchor" in s for s in declared["stages"]))

# ---------------------------------------------------------------------------
# An Arabic lesson has to be paced like any other.
#
# The section patterns were English-only, so a Grade 5 Arabic deck a teacher
# generated recovered all eleven of its slides but could name none of them:
# every stage took the flat five-minute default. The class got five minutes on
# the title screen and five on a two-minute progress check, and the teacher's
# stage list read slide-1 to slide-11 with no idea which was the Main Activity.
#
# The headings below are that deck's, verbatim.
# ---------------------------------------------------------------------------
ARABIC = """<html lang="ar" dir="rtl"><body><div class="deck-container">
 <div class="slide" id="slide-1"><h1>الجملة الاسمية والجملة الفعلية</h1>
   <p>الوقت الإجمالي: 50 دقيقة</p></div>
 <div class="slide" id="slide-2"><h2>المفردات والأهداف التعليمية</h2>
   <span>الموصى به: 2 دقيقة</span></div>
 <div class="slide" id="slide-3"><h2>النشاط الاستهلالي: مراجعة الدرس السابق</h2>
   <span>الموصى به: 5 دقائق</span></div>
 <div class="slide" id="slide-4"><h2>اختر مسار التعلم الخاص بك</h2></div>
 <div class="slide" id="slide-5"><h2>الشرح الرئيسي: نموذج بناء الجملة</h2>
   <span>الموصى به: 10 دقائق</span></div>
 <div class="slide" id="slide-6"><h2>فحص التقدم السريع</h2>
   <span>الموصى به: 2 دقيقة</span></div>
 <div class="slide" id="slide-7"><h2>النشاط الرئيسي</h2>
   <span>الموصى به: 10 دقائق</span></div>
 <div class="slide" id="slide-8"><h2>الهوية الوطنية والربط بين المواد</h2>
   <span>الموصى به: 3 دقائق</span></div>
 <div class="slide" id="slide-9"><h2>تذكرة الخروج</h2>
   <span>الموصى به: 5 دقائق</span></div>
 <div class="slide" id="slide-10"><h2>سجل الدرجات والتقييم الذاتي</h2></div>
 <div class="slide" id="slide-11"><h2>التأمل وشهادة الإنجاز</h2>
   <span>الموصى به: 5 دقائق</span></div>
</div></body></html>"""

arabic = infer_stages_from_html(ARABIC)
ids = [s["id"] for s in arabic]
check("every slide of the Arabic deck is recovered", len(arabic) == 11, str(len(arabic)))
check("the Arabic sections are named, not numbered",
      ids == ["title", "keywords", "starter", "pathway", "main-teaching",
              "progress-check", "main-activity", "connection", "exit-ticket",
              "rubric", "reflection"], str(ids))

mins = {s["id"]: s["durationSeconds"] // 60 for s in arabic}
check("the title screen is not given five minutes", mins["title"] == 1, f"{mins['title']} min")
check("the whole lesson's time is not read as the title's duration",
      mins["title"] != 50, "\"الوقت الإجمالي: 50 دقيقة\" states the lesson, not the slide")
check("a duration stated in Arabic is read", mins["main-teaching"] == 10, f"{mins['main-teaching']} min")
check("the progress check keeps its two minutes", mins["progress-check"] == 2, f"{mins['progress-check']} min")
check("pathway choice is a minute, not five", mins["pathway"] == 1, f"{mins['pathway']} min")
check("a section stating no time falls back to its framework timing",
      mins["rubric"] == 2, f"{mins['rubric']} min")
check("every stage is anchored to its own element",
      [s["anchor"] for s in arabic] == [f"slide-{i}" for i in range(1, 12)],
      str([s["anchor"] for s in arabic]))

# The English equivalent of the trap above must not be sprung either.
TOTAL_TIME = """<html><body><div class="deck">
 <div class="slide" id="s1"><h1>Photosynthesis</h1><p>Total time: 50 minutes</p></div>
 <div class="slide" id="s2"><h2>Starter</h2><span>Recommended: 5 min</span></div>
 <div class="slide" id="s3"><h2>Main Teaching</h2><span>Recommended: 10 min</span></div>
</div></body></html>"""
english = {s["id"]: s["durationSeconds"] // 60 for s in infer_stages_from_html(TOTAL_TIME)}
check("an English title slide stating the lesson total is not a 50-minute stage",
      english.get("title") == 1, f"{english.get('title')} min")


# ---------------------------------------------------------------------------
# Choosing a pathway, in English.
#
# The pathway pattern was written with \b escaped wrongly, so the compiled
# regex held two literal backspace characters and matched nothing an English
# deck could ever say. It went unnoticed because the only test for it was
# Arabic, which matched on the word list instead and passed regardless.
#
# It must also not fire on the word alone: one deck headed a slide "Extension
# Pathway Challenge Task", and a biology lesson on metabolic pathways is not a
# chooser.
# ---------------------------------------------------------------------------
for heading, want in [
    ("Choose Your Main Activity Pathway", "pathway"),
    ("Choose Your Pathway", "pathway"),
    ("Pathway Selector", "pathway"),
    ("Select your level", "pathway"),
    ("Main Activity (10 min)", "main-activity"),
    ("Extension Pathway Challenge Task", None),
    ("Metabolic pathways of respiration", None),
]:
    got = _match_stage("slide", heading)
    got_id = got.id if got else None
    check(f'"{heading}" is recognised as {want}', got_id == want, f"got {got_id}")

passed = sum(results)
print(f"\nTOTAL {passed} passed, {len(results) - passed} failed")
sys.exit(0 if all(results) else 1)
