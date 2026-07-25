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


def _stage(stage_id: str, label: str, stage_type: str, duration: int) -> dict:
    return {"id": stage_id, "label": label, "type": stage_type, "durationSeconds": duration, "sequentialLock": True}


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
        _stage("main-activity", "Main Activity", "main-activity", 600),
        _stage("exit-ticket", "Exit Ticket", "exit-ticket", 300),
    ]
    manifest = _base_manifest("lesson-deck", subject, grade, topic, stages)
    html_sections = "\n\n".join(
        [
            _mcq_section(
                "starter",
                "Starter",
                f"Quick recall: what do you remember about <strong>{topic}</strong>?",
                [
                    (f"A correct recall statement about {topic}", True),
                    ("An unrelated statement", False),
                ],
            ),
            _mcq_section(
                "main-activity",
                "Main Activity",
                f"Which statement best describes <strong>{topic}</strong>?",
                [
                    (f"A distractor about {subject}", False),
                    (f"The correct explanation of {topic}", True),
                    (f"A common misconception about {topic}", False),
                ],
            ),
            _text_section(
                "exit-ticket", "Exit Ticket", f"In one sentence, summarise what you learned about <strong>{topic}</strong>.", "exit-answer"
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


_CANNED_GENERATORS = {
    "Interactive Lesson Deck": _gen_lesson_deck,
    "Interactive Worksheet": _gen_lesson_deck,
    "Quiz": _gen_quiz,
    "Multiple Choice": _gen_multiple_choice,
    "Poll": _gen_poll,
    "Exit Ticket": _gen_exit_ticket,
    "Flashcards": _gen_flashcards,
    "Matching": _gen_matching,
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
) -> str:
    if settings.openai_api_key:
        html = _generate_with_openai(subject, grade, topic, activity_type, objectives, difficulty, time_limit)
        if html:
            return html
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
    return filled + "\n\n" + LISM_INTEGRATION_ADDENDUM


def _generate_with_openai(subject, grade, topic, activity_type, objectives, difficulty, time_limit) -> str | None:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)

        prompt_file = _LESSON_TYPE_TO_PROMPT_FILE.get(activity_type)
        if prompt_file:
            prompt = _build_master_prompt(prompt_file, subject, grade, topic, "", objectives)
        else:
            prompt = (
                f"Create a single self-contained HTML file (inline CSS and JS, no external assets, "
                f"no markdown fences) for a {activity_type} classroom activity.\n"
                f"Subject: {subject}\nGrade: {grade}\nTopic: {topic}\n"
                f"Learning objectives: {objectives or 'not specified'}\n"
                f"Difficulty: {difficulty}\nTime limit: {time_limit} minutes.\n"
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
