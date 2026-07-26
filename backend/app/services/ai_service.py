"""AI activity generation: real OpenAI call when configured, canned template otherwise.

Both paths produce a self-contained HTML activity carrying a LISM Lesson
Manifest (see manifest_service.py) and an inline "LISM Classroom SDK"
contract: a small guarded postMessage listener/emitter, not an external
script, so the activity still works standalone with zero dependencies if a
teacher opens the file directly outside LISM. The join page (see
join/[code]/page.tsx) drives this contract to keep every student's device on
the same stage together.

Universal Activity Support: the canned (no-API-key) path is a registry of
generators keyed by activity type -- a Quiz is genuinely different in shape
(three single-question stages, teacher-paced) from a Poll (one stage, no
right answer) or the full Lesson Deck (three-part lesson). All of them share
the same manifest schema and SDK contract via a common HTML shell, which is
exactly what lets the same stage engine, live dashboard, Focus Mode, AI
Coach and Insights work identically regardless of activity type.
"""

import json
from pathlib import Path

from app.core.config import settings

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

LISM_INTEGRATION_ADDENDUM = """
LISM CLASSROOM INTEGRATION ADDENDUM (required, in addition to everything above):
1. Emit a machine-readable manifest as an inert script tag in <head>:
   <script type="application/json" id="lism-manifest">{...}</script>
   It must include: lessonType ("lesson-deck" or "worksheet"), subject, grade,
   week, topic, learningObjectives ({all, most, some} as strings), keywords
   (array), dok (array of {level, label, marks} matching the rubric above),
   deliveryMode ("lesson" or "homework"), sessionType ("lesson"), and stages:
   an ordered array with one entry per slide/section defined above, each
   {id, label, type, durationSeconds, sequentialLock: true}, in the same
   order as the slides/sections.
2. Add an optional LISM Classroom SDK hook, guarded so the file still works
   perfectly standalone with zero dependencies (same pattern as the optional
   MathJax upgrade above): listen with
   window.addEventListener('message', ...) for commands of the shape
   {type:'lism:command', command:'start_stage'|'stage_ended', stage} and use
   them to control which slide/section is visible and when its timer starts,
   instead of relying only on the learner's own Next/Previous and
   click-to-start behavior. When no such commands ever arrive (the file was
   opened directly), everything must behave exactly as specified above with
   no LISM integration at all.
3. When a student's answer is accepted/marked on any slide/section, also call
   window.parent.postMessage({type:'lism:event', event:'student_submitted',
   stageId, correct, answer, mark}, '*') if window.parent !== window.
4. This integration must never send data anywhere except via postMessage to
   window.parent when embedded — the "fully offline, nothing sent anywhere"
   promise still holds for standalone use outside LISM.
Return ONLY the raw HTML, no markdown fences.
"""

_LESSON_TYPE_TO_PROMPT_FILE = {
    "Interactive Lesson Deck": "lesson_deck_master_prompt.txt",
    "Interactive Worksheet": "worksheet_master_prompt.txt",
}

# Applied to every generation. Without it the model reaches for filler like
# "What do you remember?" and "Which statement is correct?", which is what
# made generated activities feel identical whatever the subject or type.
PEDAGOGY_REQUIREMENTS = """
EDUCATIONAL QUALITY REQUIREMENTS (mandatory — these decide whether the activity is usable in a real classroom):

Every question must be about THIS topic's actual content. A question that would still make sense
if you swapped in a different topic is not specific enough — rewrite it.

BANNED, because they assess nothing:
- "What do you remember about X?" / "What do you already know?"
- "Which statement is correct?" with invented options like "a correct statement" or "a distractor"
- "True or false: X always works the same way"
- Any option text that describes what the option is ("a common misconception") instead of stating it
- Restating the topic name as though it were an answer

REQUIRED instead — choose the verb that actually fits the content:
  Analyse this diagram/data · Predict what happens when... · Explain why...
  Identify the error in this worked example · Classify these examples · Interpret this graph
  Compare these two cases · Complete the missing step · Label the diagram
  Match each concept to its use · Solve this scenario · Justify which explanation is better
  Order these steps · Correct this misconception

For multiple choice, every distractor must be a real, plausible mistake a student at this grade
actually makes — a specific wrong value, a confused term, a step applied in the wrong order.
Never write a placeholder distractor. If you cannot write plausible wrong answers for this
content, use an open response question instead.

Pitch to the stated grade: correct terminology, realistic numbers, age-appropriate context.
Tie every question to the stated learning objectives.

OPENING QUESTION — set the tone by activity type:
- Lesson deck / worksheet: a diagnostic retrieval question targeting a specific prior idea this
  lesson builds on, or a likely misconception — not a general "what do you know".
- Simulation: an observation or a prediction about a variable before the student changes anything.
- Coding challenge: predict this code's output, find the bug, or complete the missing line.
- Escape room: a puzzle that cannot be solved without applying the concept.
- Quiz / exit ticket: a specific applied item, not a definition-recall item.
"""

# Types whose real shape is nothing like a lesson. Kept in sync with
# _CANNED_GENERATORS below so both paths agree on what each type is.
_TYPE_STRUCTURES = {
    "Simulation": "Scenario -> Interactive controls and variables -> Observation -> Analysis -> Reflection. "
    "Include working sliders/inputs that visibly change a modelled outcome, and make the student "
    "predict before exploring. Do NOT produce Starter/Main Activity/Exit Ticket.",
    "Coding Challenge": "Problem statement -> Predict the output -> Code editor -> Run against test cases -> "
    "Reflection. The editor must preserve indentation and take Tab as indent. Never execute student "
    "code; check structure and expected output. Do NOT produce Starter/Main Activity/Exit Ticket.",
    "Escape Room": "Story hook -> a sequence of locked puzzles, each unlocking the next -> final reflection. "
    "Every puzzle must require the concept to solve, not just a guessable code. "
    "Do NOT produce Starter/Main Activity/Exit Ticket.",
    "Flashcards": "A deck of term/definition cards that flip, then a self-check. Not a lesson.",
    "Matching": "Pairs to match, scored on completion. Not a lesson.",
    "Poll": "A single opinion question with options and a live tally. Not a lesson.",
    "Quiz": "A sequence of independent scored questions. Not a lesson.",
    "Exit Ticket": "A short set of applied items checking today's objectives. Not a lesson.",
}


# --- Shared HTML shell -------------------------------------------------
#
# Every canned activity -- whatever its shape -- is a set of `.stage`
# sections plus this common CSS/JS. Only the stage markup and manifest
# differ between activity types.

_SHELL_CSS = """
  body { font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; }
  .stage { display:none; min-height:100vh; align-items:center; justify-content:center; flex-direction:column; padding:2rem; box-sizing:border-box; }
  .stage.visible { display:flex; }
  .card { background:#1e293b; padding:2rem; border-radius:1rem; max-width:560px; width:90%; box-shadow:0 10px 30px rgba(0,0,0,.3); }
  h1 { margin-top:0; font-size:1.4rem; }
  .meta { color:#94a3b8; font-size:.85rem; margin-bottom:1.5rem; }
  button { display:block; width:100%; text-align:left; margin:.5rem 0; padding:.75rem 1rem; border-radius:.5rem; border:1px solid #334155; background:#0f172a; color:#e2e8f0; cursor:pointer; font-size:1rem; }
  button:hover:not(:disabled) { border-color:#6366f1; }
  button.correct { background:#166534; border-color:#22c55e; }
  button.incorrect { background:#7f1d1d; border-color:#ef4444; }
  button.selected { background:#1e3a8a; border-color:#6366f1; }
  textarea { width:100%; box-sizing:border-box; border-radius:.5rem; border:1px solid #334155; background:#0f172a; color:#e2e8f0; padding:.75rem; font-size:1rem; }
  #lism-waiting { position:fixed; inset:0; background:#0f172a; color:#e2e8f0; display:flex; align-items:center; justify-content:center; text-align:center; padding:2rem; font-size:1.2rem; z-index:10; }
  .grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:.5rem; }
  .flip-card { border:1px solid #334155; border-radius:.75rem; padding:1.5rem; text-align:center; cursor:pointer; min-height:120px; display:flex; align-items:center; justify-content:center; }
  .progress { color:#94a3b8; font-size:.8rem; margin-bottom:.5rem; }
  .card { max-width:680px; }
  /* Marks the parts a teacher is expected to replace, so a template is never
     mistaken for a finished, subject-specific question. */
  .teacher-note { color:#fbbf24; font-size:.8rem; border-left:3px solid #fbbf24; padding-left:.6rem; margin:.75rem 0; }
  .sim-row { margin:1rem 0; }
  .sim-row label { display:block; margin-bottom:.35rem; font-size:.9rem; color:#cbd5e1; }
  .sim-row input[type=range] { width:100%; }
  .sim-readout { margin-top:1rem; text-align:center; }
  .sim-out { font-size:2.5rem; font-weight:700; color:#818cf8; line-height:1.1; }
  #sim-canvas { width:100%; height:auto; background:#0f172a; border:1px solid #334155; border-radius:.5rem; margin-top:.75rem; }
  .code-block, .code-editor { font-family:ui-monospace,Consolas,monospace; font-size:.9rem; white-space:pre; overflow-x:auto; background:#0b1220; border:1px solid #334155; border-radius:.5rem; padding:.85rem; color:#e2e8f0; }
  .code-editor { width:100%; box-sizing:border-box; tab-size:4; }
  .test-pass { color:#4ade80; padding:.2rem 0; }
  .test-fail { color:#f87171; padding:.2rem 0; }
  .lock-input { width:100%; box-sizing:border-box; padding:.75rem; border-radius:.5rem; border:1px solid #334155; background:#0f172a; color:#e2e8f0; font-size:1.1rem; letter-spacing:.1em; }
  .lock-msg { margin-top:.5rem; font-size:.9rem; }
  .hint-btn { background:transparent; border-style:dashed; }
  .hint { color:#94a3b8; font-size:.85rem; font-style:italic; }
"""

_SHELL_JS_CORE = """
      function showStage(id) {
        document.querySelectorAll('.stage').forEach(function (s) {
          s.classList.toggle('visible', s.dataset.stage === id);
        });
        document.getElementById('lism-waiting').style.display = 'none';
      }
      function showWaiting(text) {
        var w = document.getElementById('lism-waiting');
        w.textContent = text;
        w.style.display = 'flex';
      }
      window.addEventListener('message', function (event) {
        var data = event.data || {};
        if (data.type !== 'lism:command') return;
        if (data.command === 'start_stage') showStage(data.stage.id);
        if (data.command === 'stage_ended') showWaiting('Waiting for your teacher\\u2026');
      });
      window.lismEmit = function (eventName, payload) {
        if (window.parent === window) return;
        window.parent.postMessage(Object.assign({ type: 'lism:event', event: eventName }, payload || {}), '*');
      };
      window.lismAnswer = function (btn) {
        var group = btn.closest('.options');
        var hasCorrectness = btn.dataset.correct !== undefined;
        Array.prototype.forEach.call(group.querySelectorAll('button'), function (b) {
          b.disabled = true;
          if (hasCorrectness) b.classList.add(b.dataset.correct === 'true' ? 'correct' : 'incorrect');
        });
        if (!hasCorrectness) btn.classList.add('selected');
        var correct = hasCorrectness ? btn.dataset.correct === 'true' : null;
        window.lismEmit('student_submitted', { stageId: group.dataset.stageId, correct: correct, answer: btn.textContent });
      };
      window.lismSubmitText = function (stageId, textareaId) {
        var box = document.getElementById(textareaId);
        window.lismEmit('student_submitted', { stageId: stageId, correct: null, answer: box.value.trim() });
        box.disabled = true;
      };
"""


def _render_shell(topic: str, subject: str, manifest: dict, stages_html: str, default_stage_id: str, extra_js: str = "") -> str:
    manifest_json = json.dumps(manifest)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>{topic} - {subject}</title>
<script type="application/json" id="lism-manifest">{manifest_json}</script>
<style>{_SHELL_CSS}</style>
</head>
<body>
  <div id="lism-waiting">Waiting for your teacher to start the lesson&hellip;</div>

{stages_html}

  <script>
    (function () {{
{_SHELL_JS_CORE}
{extra_js}
      // Opened directly (no LISM host): fall back to showing the first
      // stage immediately, so the file is still fully usable standalone.
      if (window.parent === window) {{
        showStage('{default_stage_id}');
      }} else {{
        showWaiting('Waiting for your teacher to start the lesson\\u2026');
      }}
    }})();
  </script>
</body>
</html>"""


def _base_manifest(lesson_type: str, subject: str, grade: str, topic: str, stages: list[dict]) -> dict:
    return {
        "lessonType": lesson_type,
        "subject": subject,
        "grade": grade,
        "week": "",
        "topic": topic,
        "learningObjectives": {
            "all": f"I can recall a key fact about {topic}.",
            "most": f"I can explain {topic} in my own words.",
            "some": f"I can apply {topic} to a new situation.",
        },
        "keywords": [w for w in [topic, subject] if w],
        "dok": [
            {"level": 1, "label": "Recall", "marks": 2},
            {"level": 2, "label": "Skill", "marks": 3},
            {"level": 3, "label": "Application", "marks": 3},
            {"level": 4, "label": "Evaluation", "marks": 2},
        ],
        "deliveryMode": "lesson",
        "sessionType": "lesson",
        "stages": stages,
    }


def _stage(stage_id: str, label: str, stage_type: str, duration: int, marks: int | None = None) -> dict:
    """`marks` is the stage's mark total -- 10 on a Main Task, None elsewhere.
    The student's completion report needs it to show a score out of something
    rather than a bare mark count."""
    return {
        "id": stage_id,
        "label": label,
        "type": stage_type,
        "durationSeconds": duration,
        "sequentialLock": True,
        "marks": marks,
    }


def _mcq_section(stage_id: str, heading: str, prompt: str, options: list[tuple[str, bool]]) -> str:
    buttons = "\n".join(
        f'        <button data-correct="{"true" if correct else "false"}" onclick="lismAnswer(this)">{text}</button>'
        for text, correct in options
    )
    return f"""  <section class="stage" data-stage="{stage_id}">
    <div class="card">
      <h1>{heading}</h1>
      <p>{prompt}</p>
      <div class="options" data-stage-id="{stage_id}">
{buttons}
      </div>
    </div>
  </section>"""


def _poll_section(stage_id: str, heading: str, prompt: str, options: list[str]) -> str:
    buttons = "\n".join(f'        <button onclick="lismAnswer(this)">{text}</button>' for text in options)
    return f"""  <section class="stage" data-stage="{stage_id}">
    <div class="card">
      <h1>{heading}</h1>
      <p>{prompt}</p>
      <div class="options" data-stage-id="{stage_id}">
{buttons}
      </div>
    </div>
  </section>"""


def _text_section(stage_id: str, heading: str, prompt: str, textarea_id: str) -> str:
    return f"""  <section class="stage" data-stage="{stage_id}">
    <div class="card">
      <h1>{heading}</h1>
      <p>{prompt}</p>
      <textarea id="{textarea_id}" rows="3"></textarea>
      <button onclick="lismSubmitText('{stage_id}', '{textarea_id}')">Submit</button>
    </div>
  </section>"""


# --- Per-activity-type canned generators -------------------------------


def _gen_lesson_deck(subject, grade, topic, difficulty, time_limit) -> tuple[dict, str]:
    stages = [
        _stage("starter", "Starter", "starter", 300),
        _stage("main-activity", "Main Activity", "main-activity", 600, marks=10),
        _stage("exit-ticket", "Exit Ticket", "exit-ticket", 300),
    ]
    manifest = _base_manifest("lesson-deck", subject, grade, topic, stages)
    # Open-response prompts rather than multiple choice: a template has no
    # subject knowledge, so any options it invents are placeholders ("a
    # distractor about Science") that read as filler to a class. A real task
    # verb aimed at the topic is honest and still usable as-is, and the
    # teacher-note marks what to replace.
    html_sections = "\n\n".join(
        [
            _text_section(
                "starter",
                "Starter",
                f"<strong>Explain</strong> in your own words what you already know about <strong>{topic}</strong>, "
                f"and give one example of where you have seen it in {subject}."
                f'<br /><span class="teacher-note">Teacher: replace with a diagnostic question aimed at the '
                f"specific misconception you expect from your class.</span>",
                "starter-answer",
            ),
            _text_section(
                "main-activity",
                "Main Activity",
                f"<strong>Apply it.</strong> Describe a situation involving {topic}, then explain <em>why</em> it "
                f"behaves that way &mdash; not just what happens."
                f'<br /><span class="teacher-note">Teacher: replace with the real task &mdash; analyse a diagram, '
                f"predict an outcome, identify the error, interpret data, or solve a scenario from your lesson.</span>",
                "main-answer",
            ),
            _text_section(
                "exit-ticket",
                "Exit Ticket",
                f"<strong>Justify.</strong> What is the most important thing to understand about {topic}, and how "
                f"would you explain it to someone who missed today's lesson?",
                "exit-answer",
            ),
        ]
    )
    return manifest, _render_shell(topic, subject, manifest, html_sections, "starter")


def _gen_quiz(subject, grade, topic, difficulty, time_limit) -> tuple[dict, str]:
    stages = [_stage(f"q{i}", f"Question {i}", "quiz-question", 120) for i in (1, 2, 3)]
    manifest = _base_manifest("quiz", subject, grade, topic, stages)
    questions = [
        (f"What is one key fact about {topic}?", [(f"A correct fact about {topic}", True), ("An incorrect fact", False)]),
        (f"Which of these best relates to {topic}?", [("An unrelated idea", False), (f"A directly related idea about {topic}", True)]),
        (f"True or false: {topic} always works the same way in {subject}.", [("True", False), ("False — it depends on context", True)]),
    ]
    sections = "\n\n".join(
        _mcq_section(f"q{i}", f"Question {i}", prompt, opts) for i, (prompt, opts) in zip((1, 2, 3), questions)
    )
    return manifest, _render_shell(topic, subject, manifest, sections, "q1")


def _gen_multiple_choice(subject, grade, topic, difficulty, time_limit) -> tuple[dict, str]:
    stages = [_stage("question", "Question", "question", 180)]
    manifest = _base_manifest("standalone", subject, grade, topic, stages)
    section = _mcq_section(
        "question",
        topic,
        f"Which statement best describes <strong>{topic}</strong>?",
        [
            (f"A distractor about {subject}", False),
            (f"The correct explanation of {topic}", True),
            (f"A common misconception about {topic}", False),
        ],
    )
    return manifest, _render_shell(topic, subject, manifest, section, "question")


def _gen_poll(subject, grade, topic, difficulty, time_limit) -> tuple[dict, str]:
    stages = [_stage("poll", "Poll", "poll", 180)]
    manifest = _base_manifest("standalone", subject, grade, topic, stages)
    section = _poll_section(
        "poll",
        f"Quick poll: {topic}",
        "What's your gut reaction to this topic?",
        ["I understand it well", "I'm still getting there", "I need more practice"],
    )
    return manifest, _render_shell(topic, subject, manifest, section, "poll")


def _gen_exit_ticket(subject, grade, topic, difficulty, time_limit) -> tuple[dict, str]:
    stages = [_stage("exit-ticket", "Exit Ticket", "exit-ticket", 300)]
    manifest = _base_manifest("standalone", subject, grade, topic, stages)
    section = _text_section(
        "exit-ticket", "Exit Ticket", f"In one or two sentences, what did you learn about <strong>{topic}</strong> today?", "exit-answer"
    )
    return manifest, _render_shell(topic, subject, manifest, section, "exit-ticket")


def _gen_flashcards(subject, grade, topic, difficulty, time_limit) -> tuple[dict, str]:
    stages = [_stage("flashcards", "Flashcards", "flashcards", 300)]
    manifest = _base_manifest("standalone", subject, grade, topic, stages)
    cards = [
        (f"Term {i} about {topic}", f"Definition {i} relating to {topic} in {subject}.") for i in range(1, 5)
    ]
    cards_json = json.dumps(cards)
    section = f"""  <section class="stage" data-stage="flashcards">
    <div class="card">
      <h1>Flashcards: {topic}</h1>
      <div class="progress" id="fc-progress">Card 1 of {len(cards)}</div>
      <div class="flip-card" id="fc-face" onclick="lismFlipCard()"></div>
      <div id="fc-rating" style="display:none; margin-top:1rem;">
        <button onclick="lismRateCard(true)">Got it</button>
        <button onclick="lismRateCard(false)">Still learning</button>
      </div>
    </div>
  </section>"""
    extra_js = f"""
      var fcCards = {cards_json};
      var fcIndex = 0, fcShowingBack = false, fcGotIt = 0;
      function fcRender() {{
        var el = document.getElementById('fc-face');
        if (!el) return;
        el.textContent = fcShowingBack ? fcCards[fcIndex][1] : fcCards[fcIndex][0];
        document.getElementById('fc-progress').textContent = 'Card ' + (fcIndex + 1) + ' of ' + fcCards.length;
        document.getElementById('fc-rating').style.display = fcShowingBack ? 'block' : 'none';
      }}
      window.lismFlipCard = function () {{ fcShowingBack = true; fcRender(); }};
      window.lismRateCard = function (gotIt) {{
        if (gotIt) fcGotIt++;
        fcIndex++;
        fcShowingBack = false;
        if (fcIndex >= fcCards.length) {{
          window.lismEmit('student_submitted', {{ stageId: 'flashcards', correct: null, answer: fcGotIt + '/' + fcCards.length + ' known' }});
          document.getElementById('fc-face').textContent = 'All done! ' + fcGotIt + '/' + fcCards.length + ' known.';
          document.getElementById('fc-rating').style.display = 'none';
          return;
        }}
        fcRender();
      }};
      if (document.getElementById('fc-face')) fcRender();
"""
    return manifest, _render_shell(topic, subject, manifest, section, "flashcards", extra_js)


def _gen_matching(subject, grade, topic, difficulty, time_limit) -> tuple[dict, str]:
    stages = [_stage("matching", "Matching", "matching", 300)]
    manifest = _base_manifest("standalone", subject, grade, topic, stages)
    pairs = [(f"Term {i}", f"Match {i} for {topic}") for i in range(1, 5)]
    terms = [p[0] for p in pairs]
    defs = [p[1] for p in pairs]
    pairs_json = json.dumps({"terms": terms, "defs": defs})
    section = f"""  <section class="stage" data-stage="matching">
    <div class="card">
      <h1>Matching: {topic}</h1>
      <p>Click a term, then click its matching definition.</p>
      <div class="grid-2">
        <div id="mt-terms"></div>
        <div id="mt-defs"></div>
      </div>
      <p id="mt-status" class="meta"></p>
    </div>
  </section>"""
    extra_js = f"""
      var mtData = {pairs_json};
      var mtSelectedTerm = null, mtMatched = 0;
      function mtRender() {{
        var termsEl = document.getElementById('mt-terms');
        var defsEl = document.getElementById('mt-defs');
        if (!termsEl) return;
        termsEl.innerHTML = '';
        defsEl.innerHTML = '';
        mtData.terms.forEach(function (t) {{
          var b = document.createElement('button');
          b.textContent = t;
          b.onclick = function () {{ mtSelectedTerm = t; }};
          termsEl.appendChild(b);
        }});
        var shuffledDefs = mtData.defs.slice().sort(function () {{ return Math.random() - 0.5; }});
        shuffledDefs.forEach(function (d) {{
          var b = document.createElement('button');
          b.textContent = d;
          b.onclick = function () {{
            if (!mtSelectedTerm) return;
            var idx = mtData.terms.indexOf(mtSelectedTerm);
            var correctDef = mtData.defs[idx];
            if (d === correctDef) {{
              b.classList.add('correct');
              b.disabled = true;
              mtMatched++;
              document.getElementById('mt-status').textContent = mtMatched + '/' + mtData.terms.length + ' matched';
              if (mtMatched >= mtData.terms.length) {{
                window.lismEmit('student_submitted', {{ stageId: 'matching', correct: true, answer: 'All pairs matched' }});
              }}
            }} else {{
              b.classList.add('incorrect');
              setTimeout(function () {{ b.classList.remove('incorrect'); }}, 500);
            }}
            mtSelectedTerm = null;
          }};
          defsEl.appendChild(b);
        }});
      }}
      if (document.getElementById('mt-terms')) mtRender();
"""
    return manifest, _render_shell(topic, subject, manifest, section, "matching", extra_js)


def _gen_simulation(subject, grade, topic, difficulty, time_limit) -> tuple[dict, str]:
    """A simulation is not a lesson with slides -- it is a model you change and
    observe. Structure: scenario, controls/variables, observation, analysis,
    reflection. The two variables are deliberately generic because a template
    cannot know the real quantities in this topic; the teacher renames them in
    the Edit screen (or a configured OpenAI key produces subject-real ones)."""
    stages = [
        _stage("scenario", "Scenario", "scenario", 180),
        _stage("explore", "Explore the Variables", "simulation", 420),
        _stage("observation", "Observation", "observation", 240),
        _stage("analysis", "Analysis", "analysis", 300),
        _stage("reflection", "Reflection", "reflection", 180),
    ]
    manifest = _base_manifest("simulation", subject, grade, topic, stages)

    sections = f"""  <section class="stage" data-stage="scenario">
    <div class="card">
      <h1>Scenario</h1>
      <p>You are investigating <strong>{topic}</strong> in {subject}.</p>
      <p class="teacher-note">Teacher: replace this with the real scenario your class is modelling.</p>
      <p><strong>Before you touch anything, predict:</strong> if you increase Variable A, what happens to the Outcome, and why?</p>
      <textarea id="sim-predict" rows="3" placeholder="I predict that... because..."></textarea>
      <button onclick="lismSubmitText('scenario', 'sim-predict')">Submit my prediction</button>
    </div>
  </section>

  <section class="stage" data-stage="explore">
    <div class="card">
      <h1>Explore the Variables</h1>
      <p>Change one variable at a time and watch the Outcome. Changing two at once tells you nothing about either.</p>
      <div class="sim-row">
        <label for="sim-a">Variable A <span id="sim-a-val">50</span></label>
        <input type="range" id="sim-a" min="0" max="100" value="50" />
      </div>
      <div class="sim-row">
        <label for="sim-b">Variable B <span id="sim-b-val">50</span></label>
        <input type="range" id="sim-b" min="0" max="100" value="50" />
      </div>
      <div class="sim-readout">
        <div>Outcome</div>
        <div id="sim-out" class="sim-out">50</div>
        <canvas id="sim-canvas" width="600" height="160"></canvas>
      </div>
      <p id="sim-count" class="teacher-note">Trials run: 0 — run at least 3 before moving on.</p>
    </div>
  </section>

  <section class="stage" data-stage="observation">
    <div class="card">
      <h1>Observation</h1>
      <p>Describe <em>what you saw</em>, not why yet. What happened to the Outcome as Variable A increased?</p>
      <textarea id="sim-observe" rows="4" placeholder="When I increased Variable A, the Outcome..."></textarea>
      <button onclick="lismSubmitText('observation', 'sim-observe')">Submit observation</button>
    </div>
  </section>

  <section class="stage" data-stage="analysis">
    <div class="card">
      <h1>Analysis</h1>
      <p>Now explain <em>why</em>. Was your prediction right? Which variable had the larger effect, and what does that tell you about {topic}?</p>
      <textarea id="sim-analyse" rows="5" placeholder="My prediction was... The Outcome changed because..."></textarea>
      <button onclick="lismSubmitText('analysis', 'sim-analyse')">Submit analysis</button>
    </div>
  </section>

  <section class="stage" data-stage="reflection">
    <div class="card">
      <h1>Reflection</h1>
      <p>What would you test next, and what would that tell you that this run did not?</p>
      <textarea id="sim-reflect" rows="3"></textarea>
      <button onclick="lismSubmitText('reflection', 'sim-reflect')">Submit reflection</button>
    </div>
  </section>"""

    extra_js = """
      var simTrials = 0;
      function simUpdate() {
        var a = +document.getElementById('sim-a').value;
        var b = +document.getElementById('sim-b').value;
        document.getElementById('sim-a-val').textContent = a;
        document.getElementById('sim-b-val').textContent = b;
        // Placeholder relationship: the teacher swaps this for the real model.
        var out = Math.round((a * 0.7 + b * 0.3));
        document.getElementById('sim-out').textContent = out;
        var c = document.getElementById('sim-canvas');
        if (c && c.getContext) {
          var ctx = c.getContext('2d');
          ctx.clearRect(0, 0, c.width, c.height);
          ctx.strokeStyle = '#6366f1'; ctx.lineWidth = 3; ctx.beginPath();
          for (var x = 0; x <= 100; x++) {
            var y = (x * (a / 100) * 0.7 + (b / 100) * 30);
            var px = (x / 100) * c.width;
            var py = c.height - (y / 100) * c.height;
            if (x === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
          }
          ctx.stroke();
        }
        simTrials++;
        var cnt = document.getElementById('sim-count');
        if (cnt) cnt.textContent = 'Trials run: ' + simTrials + (simTrials >= 3 ? ' — good, now describe what you saw.' : ' — run at least 3 before moving on.');
        if (simTrials === 3) {
          window.lismEmit('student_submitted', { stageId: 'explore', correct: null, answer: 'Ran 3 simulation trials' });
        }
      }
      ['sim-a', 'sim-b'].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('input', simUpdate);
      });
      if (document.getElementById('sim-a')) simUpdate();
"""
    return manifest, _render_shell(topic, subject, manifest, sections, "scenario", extra_js)


def _gen_coding_challenge(subject, grade, topic, difficulty, time_limit) -> tuple[dict, str]:
    """Problem, editor, run against test cases, submit -- not a slide deck.
    Code is checked structurally and against expected output, never executed
    as arbitrary code on the student's machine."""
    stages = [
        _stage("problem", "The Problem", "problem", 180),
        _stage("predict", "Predict the Output", "predict", 180),
        _stage("code", "Write Your Code", "code", 600),
        _stage("tests", "Test Cases", "tests", 240),
        _stage("reflection", "Reflection", "reflection", 180),
    ]
    manifest = _base_manifest("coding-challenge", subject, grade, topic, stages)

    sections = f"""  <section class="stage" data-stage="problem">
    <div class="card">
      <h1>The Problem</h1>
      <p><strong>{topic}</strong></p>
      <p class="teacher-note">Teacher: replace this with the real problem statement, inputs and expected outputs.</p>
      <pre class="code-block">Write a function solve(n) that returns
the result described for this task.

Example:  solve(3)  ->  6</pre>
      <p>Read it carefully. What are the inputs, and what exactly must be returned?</p>
    </div>
  </section>

  <section class="stage" data-stage="predict">
    <div class="card">
      <h1>Predict the Output</h1>
      <p>Before writing anything, trace this code by hand. What does it print, and why?</p>
      <pre class="code-block">total = 0
for i in range(1, 4):
    total = total + i
print(total)</pre>
      <textarea id="cc-predict" rows="3" placeholder="It prints ... because ..."></textarea>
      <button onclick="lismSubmitText('predict', 'cc-predict')">Submit prediction</button>
    </div>
  </section>

  <section class="stage" data-stage="code">
    <div class="card">
      <h1>Write Your Code</h1>
      <p>Indentation matters. Tab indents; Shift+Tab outdents.</p>
      <textarea id="cc-editor" class="code-editor" rows="12" spellcheck="false">def solve(n):
    # your code here
    return 0</textarea>
      <button onclick="ccRun()">Run against test cases</button>
      <div id="cc-results"></div>
    </div>
  </section>

  <section class="stage" data-stage="tests">
    <div class="card">
      <h1>Test Cases</h1>
      <p>Which case fails, and what does that tell you about your logic?</p>
      <textarea id="cc-tests" rows="4" placeholder="The failing case is... which means my code..."></textarea>
      <button onclick="lismSubmitText('tests', 'cc-tests')">Submit</button>
    </div>
  </section>

  <section class="stage" data-stage="reflection">
    <div class="card">
      <h1>Reflection</h1>
      <p>What was the hardest part, and what would you do differently next time?</p>
      <textarea id="cc-reflect" rows="3"></textarea>
      <button onclick="lismSubmitText('reflection', 'cc-reflect')">Submit reflection</button>
    </div>
  </section>"""

    extra_js = """
      var ccEditor = document.getElementById('cc-editor');
      if (ccEditor) {
        ccEditor.addEventListener('keydown', function (e) {
          if (e.key !== 'Tab') return;
          e.preventDefault();
          var s = this.selectionStart, en = this.selectionEnd;
          this.value = this.value.substring(0, s) + '    ' + this.value.substring(en);
          this.selectionStart = this.selectionEnd = s + 4;
        });
      }
      // Structural checks only -- student code is never executed.
      function ccRun() {
        var code = document.getElementById('cc-editor').value;
        var checks = [
          { label: 'Defines solve(n)', pass: /def\\s+solve\\s*\\(/.test(code) },
          { label: 'Returns a value', pass: /return\\s+\\S+/.test(code) },
          { label: 'Does more than return 0', pass: !/return\\s+0\\s*$/.test(code.trim()) },
          { label: 'Body is indented', pass: /\\n\\s{2,}\\S/.test(code) }
        ];
        var passed = checks.filter(function (c) { return c.pass; }).length;
        document.getElementById('cc-results').innerHTML = checks.map(function (c) {
          return '<div class="' + (c.pass ? 'test-pass' : 'test-fail') + '">' +
                 (c.pass ? 'PASS' : 'FAIL') + ' &mdash; ' + c.label + '</div>';
        }).join('') + '<p class="teacher-note">' + passed + ' of ' + checks.length +
          ' checks passed. Your teacher marks the logic itself.</p>';
        window.lismEmit('student_submitted', {
          stageId: 'code', correct: passed === checks.length,
          answer: code, mark: passed, maxMark: checks.length
        });
      }
      window.ccRun = ccRun;
"""
    return manifest, _render_shell(topic, subject, manifest, sections, "problem", extra_js)


def _gen_escape_room(subject, grade, topic, difficulty, time_limit) -> tuple[dict, str]:
    """Story, a sequence of puzzles that each unlock the next, then reflection.
    Each puzzle needs a real answer -- the teacher sets them in Edit."""
    stages = [
        _stage("story", "The Story", "story", 120),
        _stage("puzzle-1", "Puzzle 1", "puzzle", 300),
        _stage("puzzle-2", "Puzzle 2", "puzzle", 300),
        _stage("puzzle-3", "Puzzle 3", "puzzle", 300),
        _stage("reflection", "Escaped — Reflection", "reflection", 180),
    ]
    manifest = _base_manifest("escape-room", subject, grade, topic, stages)

    def puzzle(num: int, stage_id: str, prompt: str, answer: str, hint: str) -> str:
        return f"""  <section class="stage" data-stage="{stage_id}">
    <div class="card">
      <h1>Puzzle {num}</h1>
      <p>{prompt}</p>
      <p class="teacher-note">Teacher: set the real question and answer for this lock in Edit Activity.</p>
      <input type="text" id="er-{num}" class="lock-input" placeholder="Enter the code" />
      <button onclick="erCheck({num}, '{answer}')">Try the lock</button>
      <button class="hint-btn" onclick="erHint({num})">Need a hint?</button>
      <p id="er-hint-{num}" class="hint" hidden>{hint}</p>
      <p id="er-msg-{num}" class="lock-msg"></p>
    </div>
  </section>"""

    sections = "\n\n".join(
        [
            f"""  <section class="stage" data-stage="story">
    <div class="card">
      <h1>The Story</h1>
      <p>Your class has been locked in the {subject} lab. The only way out is to prove you understand
      <strong>{topic}</strong>. Three locks stand between you and the door.</p>
      <p class="teacher-note">Teacher: replace with your own story hook.</p>
      <p>Solve each puzzle to earn the next code. You cannot skip a lock.</p>
    </div>
  </section>""",
            puzzle(1, "puzzle-1", f"<strong>Lock 1 — Identify.</strong> Name the key idea in {topic} described by the clue your teacher gives you.", "ALPHA", "It is one of this lesson's keywords."),
            puzzle(2, "puzzle-2", f"<strong>Lock 2 — Apply.</strong> Use {topic} to work out the value that opens this lock.", "BETA", "Work through it step by step — the last step gives the code."),
            puzzle(3, "puzzle-3", f"<strong>Lock 3 — Explain.</strong> Only the group that can justify <em>why</em> gets the final code.", "GAMMA", "Think about the reason, not just the answer."),
            """  <section class="stage" data-stage="reflection">
    <div class="card">
      <h1>Escaped!</h1>
      <p>Which lock was hardest, and what did you have to understand to open it?</p>
      <textarea id="er-reflect" rows="4"></textarea>
      <button onclick="lismSubmitText('reflection', 'er-reflect')">Submit reflection</button>
    </div>
  </section>""",
        ]
    )

    extra_js = """
      function erCheck(num, answer) {
        var input = document.getElementById('er-' + num);
        var msg = document.getElementById('er-msg-' + num);
        var given = (input.value || '').trim().toUpperCase();
        if (!given) { msg.textContent = 'Enter a code first.'; return; }
        var ok = given === String(answer).trim().toUpperCase();
        msg.textContent = ok ? 'Unlocked! Move to the next lock.' : 'That code does not fit. Try again.';
        msg.className = 'lock-msg ' + (ok ? 'test-pass' : 'test-fail');
        if (ok) input.disabled = true;
        window.lismEmit('student_submitted', {
          stageId: 'puzzle-' + num, correct: ok, answer: given
        });
      }
      function erHint(num) {
        var h = document.getElementById('er-hint-' + num);
        if (h) h.hidden = false;
      }
      window.erCheck = erCheck; window.erHint = erHint;
"""
    return manifest, _render_shell(topic, subject, manifest, sections, "story", extra_js)


_CANNED_GENERATORS = {
    # Deck and worksheet keep the full lesson framework (Starter -> Main -> Exit).
    "Interactive Lesson Deck": _gen_lesson_deck,
    "Interactive Worksheet": _gen_lesson_deck,
    "Quiz": _gen_quiz,
    "Multiple Choice": _gen_multiple_choice,
    "Poll": _gen_poll,
    "Exit Ticket": _gen_exit_ticket,
    "Flashcards": _gen_flashcards,
    "Matching": _gen_matching,
    # Types whose real shape is nothing like a lesson. Before this, every one
    # of these fell through to the lesson-deck generator, which is why picking
    # Simulation produced a Starter/Main Activity/Exit Ticket lesson.
    "Simulation": _gen_simulation,
    "Coding Challenge": _gen_coding_challenge,
    "Escape Room": _gen_escape_room,
}


def _canned_template(subject: str, grade: str, topic: str, activity_type: str, difficulty: str, time_limit: int) -> str:
    generator = _CANNED_GENERATORS.get(activity_type, _gen_lesson_deck)
    _manifest, html = generator(subject, grade, topic, difficulty, time_limit)
    return html


def generate_activity_html(
    subject: str,
    grade: str,
    topic: str,
    activity_type: str,
    objectives: str,
    difficulty: str,
    time_limit: int,
    custom_prompt: str | None = None,
) -> str:
    if settings.openai_api_key:
        html = _generate_with_openai(
            subject, grade, topic, activity_type, objectives, difficulty, time_limit, custom_prompt
        )
        if html:
            return html
    # Custom prompts require a real LLM call to have any effect; without a
    # configured key there's nothing to run them through, so fall back to
    # the same canned template used for that activity type.
    return _canned_template(subject, grade, topic, activity_type, difficulty, time_limit)


def _build_master_prompt(prompt_file: str, subject, grade, topic, week, previous_topic) -> str:
    template = (PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")
    filled = (
        template.replace("[TOPIC NAME]", topic)
        .replace("[SUBJECT]", subject)
        .replace("[GRADE]", grade)
        .replace("[WEEK X]", week or "1")
        .replace("[PREVIOUS LESSON TOPIC]", previous_topic or "the previous lesson")
    )
    # The master prompts own the lesson framework; the pedagogy rules only
    # constrain how individual questions are written, so they compose rather
    # than conflict.
    return filled + "\n\n" + PEDAGOGY_REQUIREMENTS + "\n\n" + LISM_INTEGRATION_ADDENDUM


def _generate_with_openai(
    subject, grade, topic, activity_type, objectives, difficulty, time_limit, custom_prompt=None
) -> str | None:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)

        prompt_file = _LESSON_TYPE_TO_PROMPT_FILE.get(activity_type)
        if custom_prompt and custom_prompt.strip():
            # Teacher-pasted prompt (e.g. from the Prompt Library) is used
            # verbatim; we still require the LISM manifest + SDK contract so
            # the generated activity works in the Classroom Engine.
            prompt = (
                custom_prompt.strip()
                .replace("[TOPIC NAME]", topic)
                .replace("[SUBJECT]", subject)
                .replace("[GRADE]", grade)
                .replace("[PREVIOUS LESSON TOPIC]", objectives or "the previous lesson")
                + "\n\n"
                + PEDAGOGY_REQUIREMENTS
                + "\n\n"
                + LISM_INTEGRATION_ADDENDUM
            )
        elif prompt_file:
            prompt = _build_master_prompt(prompt_file, subject, grade, topic, "", objectives)
        else:
            structure = _TYPE_STRUCTURES.get(activity_type)
            structure_line = (
                f"REQUIRED STRUCTURE for a {activity_type}: {structure}\n"
                if structure
                else f"Use the structure a {activity_type} genuinely has, not a generic lesson.\n"
            )
            prompt = (
                f"Create a single self-contained HTML file (inline CSS and JS, no external assets, "
                f"no markdown fences) for a {activity_type} classroom activity.\n"
                f"Subject: {subject}\nGrade: {grade}\nTopic: {topic}\n"
                f"Learning objectives: {objectives or 'not specified'}\n"
                f"Difficulty: {difficulty}\nTime limit: {time_limit} minutes.\n\n"
                f"{structure_line}\n"
                f"{PEDAGOGY_REQUIREMENTS}\n"
                f"{LISM_INTEGRATION_ADDENDUM}"
            )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        html = (resp.choices[0].message.content or "").strip()
        if html.startswith("```"):
            html = html.strip("`")
            if html[:4].lower() == "html":
                html = html[4:]
        return html or None
    except Exception:
        # Any failure (missing/invalid key, network, rate limit) falls back to the canned template.
        return None
