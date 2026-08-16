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

from app.services.manifest_service import extract_manifest, infer_stages_from_html  # noqa: E402

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

passed = sum(results)
print(f"\nTOTAL {passed} passed, {len(results) - passed} failed")
sys.exit(0 if all(results) else 1)
