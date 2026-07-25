"""AI activity generation: real OpenAI call when configured, canned template otherwise.

Both paths produce a self-contained HTML activity carrying a LISM Lesson
Manifest (see manifest_service.py) and an inline "LISM Classroom SDK"
contract: a small guarded postMessage listener/emitter, not an external
script, so the activity still works standalone with zero dependencies if a
teacher opens the file directly outside LISM. The join page (see
join/[code]/page.tsx) drives this contract to keep every student's device on
the same stage together.
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


def _canned_manifest(subject: str, grade: str, topic: str) -> dict:
    return {
        "lessonType": "lesson-deck",
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
        "stages": [
            {"id": "starter", "label": "Starter", "type": "starter", "durationSeconds": 300, "sequentialLock": True},
            {
                "id": "main-activity",
                "label": "Main Activity",
                "type": "main-activity",
                "durationSeconds": 600,
                "sequentialLock": True,
            },
            {
                "id": "exit-ticket",
                "label": "Exit Ticket",
                "type": "exit-ticket",
                "durationSeconds": 300,
                "sequentialLock": True,
            },
        ],
    }


def _canned_template(subject: str, grade: str, topic: str, activity_type: str, difficulty: str, time_limit: int) -> str:
    manifest_json = json.dumps(_canned_manifest(subject, grade, topic))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>{topic} - {subject}</title>
<script type="application/json" id="lism-manifest">{manifest_json}</script>
<style>
  body {{ font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; }}
  .stage {{ display:none; min-height:100vh; align-items:center; justify-content:center; flex-direction:column; padding:2rem; box-sizing:border-box; }}
  .stage.visible {{ display:flex; }}
  .card {{ background:#1e293b; padding:2rem; border-radius:1rem; max-width:520px; width:90%; box-shadow:0 10px 30px rgba(0,0,0,.3); }}
  h1 {{ margin-top:0; font-size:1.4rem; }}
  .meta {{ color:#94a3b8; font-size:.85rem; margin-bottom:1.5rem; }}
  button {{ display:block; width:100%; text-align:left; margin:.5rem 0; padding:.75rem 1rem; border-radius:.5rem; border:1px solid #334155; background:#0f172a; color:#e2e8f0; cursor:pointer; font-size:1rem; }}
  button:hover:not(:disabled) {{ border-color:#6366f1; }}
  button.correct {{ background:#166534; border-color:#22c55e; }}
  button.incorrect {{ background:#7f1d1d; border-color:#ef4444; }}
  textarea {{ width:100%; box-sizing:border-box; border-radius:.5rem; border:1px solid #334155; background:#0f172a; color:#e2e8f0; padding:.75rem; font-size:1rem; }}
  #lism-waiting {{ position:fixed; inset:0; background:#0f172a; color:#e2e8f0; display:flex; align-items:center; justify-content:center; text-align:center; padding:2rem; font-size:1.2rem; z-index:10; }}
</style>
</head>
<body>
  <div id="lism-waiting">Waiting for your teacher to start the lesson&hellip;</div>

  <section class="stage" data-stage="starter">
    <div class="card">
      <h1>Starter</h1>
      <div class="meta">{subject} &middot; Grade {grade} &middot; {difficulty}</div>
      <p>Quick recall: what do you remember about <strong>{topic}</strong>?</p>
      <div class="options" data-stage-id="starter">
        <button data-correct="true" onclick="lismAnswer(this)">A correct recall statement about {topic}</button>
        <button data-correct="false" onclick="lismAnswer(this)">An unrelated statement</button>
      </div>
    </div>
  </section>

  <section class="stage" data-stage="main-activity">
    <div class="card">
      <h1>Main Activity</h1>
      <div class="meta">{time_limit} min</div>
      <p>Which statement best describes <strong>{topic}</strong>?</p>
      <div class="options" data-stage-id="main-activity">
        <button data-correct="false" onclick="lismAnswer(this)">A distractor about {subject}</button>
        <button data-correct="true" onclick="lismAnswer(this)">The correct explanation of {topic}</button>
        <button data-correct="false" onclick="lismAnswer(this)">A common misconception about {topic}</button>
      </div>
    </div>
  </section>

  <section class="stage" data-stage="exit-ticket">
    <div class="card">
      <h1>Exit Ticket</h1>
      <p>In one sentence, summarise what you learned about <strong>{topic}</strong>.</p>
      <textarea id="exit-answer" rows="3"></textarea>
      <button onclick="lismSubmitExit()">Submit</button>
    </div>
  </section>

  <script>
    (function () {{
      function showStage(id) {{
        document.querySelectorAll('.stage').forEach(function (s) {{
          s.classList.toggle('visible', s.dataset.stage === id);
        }});
        document.getElementById('lism-waiting').style.display = 'none';
      }}
      function showWaiting(text) {{
        var w = document.getElementById('lism-waiting');
        w.textContent = text;
        w.style.display = 'flex';
      }}
      window.addEventListener('message', function (event) {{
        var data = event.data || {{}};
        if (data.type !== 'lism:command') return;
        if (data.command === 'start_stage') showStage(data.stage.id);
        if (data.command === 'stage_ended') showWaiting('Waiting for your teacher\\u2026');
      }});
      window.lismEmit = function (eventName, payload) {{
        if (window.parent === window) return;
        window.parent.postMessage(Object.assign({{ type: 'lism:event', event: eventName }}, payload || {{}}), '*');
      }};
      window.lismAnswer = function (btn) {{
        var group = btn.closest('.options');
        Array.prototype.forEach.call(group.querySelectorAll('button'), function (b) {{
          b.disabled = true;
          b.classList.add(b.dataset.correct === 'true' ? 'correct' : 'incorrect');
        }});
        var correct = btn.dataset.correct === 'true';
        window.lismEmit('student_submitted', {{ stageId: group.dataset.stageId, correct: correct, answer: btn.textContent }});
      }};
      window.lismSubmitExit = function () {{
        var box = document.getElementById('exit-answer');
        window.lismEmit('student_submitted', {{ stageId: 'exit-ticket', correct: null, answer: box.value.trim() }});
        box.disabled = true;
      }};
      // Opened directly (no LISM host): fall back to showing the starter stage
      // immediately after a short pause, so the file is still fully usable
      // standalone.
      if (window.parent === window) {{
        showStage('starter');
      }} else {{
        showWaiting('Waiting for your teacher to start the lesson\\u2026');
      }}
    }})();
  </script>
</body>
</html>"""


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
