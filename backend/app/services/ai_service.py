"""AI activity generation: real OpenAI call when configured, canned template otherwise.

Both paths return a single self-contained HTML string that posts a
`lism-activity-response` message to window.parent when the student answers,
so the join-page iframe can forward it to the backend regardless of how the
activity HTML was produced (AI-generated, uploaded, or canned).
"""

from app.core.config import settings

_RESPONSE_CONTRACT = (
    "When the student answers or submits, call "
    "window.parent.postMessage({type: 'lism-activity-response', correct: <bool|null>, "
    "answer: <string>}, '*') exactly once."
)


def _canned_template(subject: str, grade: str, topic: str, activity_type: str, difficulty: str, time_limit: int) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>{topic} - {subject}</title>
<style>
  body {{ font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }}
  .card {{ background:#1e293b; padding:2rem; border-radius:1rem; max-width:520px; width:90%; box-shadow:0 10px 30px rgba(0,0,0,.3); }}
  h1 {{ margin-top:0; font-size:1.4rem; }}
  .meta {{ color:#94a3b8; font-size:.85rem; margin-bottom:1.5rem; }}
  button {{ display:block; width:100%; text-align:left; margin:.5rem 0; padding:.75rem 1rem; border-radius:.5rem; border:1px solid #334155; background:#0f172a; color:#e2e8f0; cursor:pointer; font-size:1rem; }}
  button:hover:not(:disabled) {{ border-color:#6366f1; }}
  button.correct {{ background:#166534; border-color:#22c55e; }}
  button.incorrect {{ background:#7f1d1d; border-color:#ef4444; }}
  #result {{ margin-top:1rem; font-weight:600; min-height:1.2rem; }}
</style>
</head>
<body>
  <div class="card">
    <h1>{topic}</h1>
    <div class="meta">{subject} &middot; Grade {grade} &middot; {activity_type} &middot; {difficulty} &middot; {time_limit} min</div>
    <p>Which statement best describes <strong>{topic}</strong>?</p>
    <div id="options">
      <button data-correct="false" onclick="answer(this)">A distractor about {subject}</button>
      <button data-correct="true" onclick="answer(this)">The correct explanation of {topic}</button>
      <button data-correct="false" onclick="answer(this)">An unrelated statement</button>
      <button data-correct="false" onclick="answer(this)">A common misconception about {topic}</button>
    </div>
    <div id="result"></div>
  </div>
  <script>
    function answer(btn) {{
      document.querySelectorAll('#options button').forEach(function (b) {{
        b.disabled = true;
        b.classList.add(b.dataset.correct === 'true' ? 'correct' : 'incorrect');
      }});
      var correct = btn.dataset.correct === 'true';
      document.getElementById('result').textContent = correct ? 'Correct!' : 'Not quite.';
      window.parent.postMessage({{ type: 'lism-activity-response', correct: correct, answer: btn.textContent }}, '*');
    }}
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


def _generate_with_openai(subject, grade, topic, activity_type, objectives, difficulty, time_limit) -> str | None:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        prompt = (
            f"Create a single self-contained HTML file (inline CSS and JS, no external assets, "
            f"no markdown fences) for a {activity_type} classroom activity.\n"
            f"Subject: {subject}\nGrade: {grade}\nTopic: {topic}\n"
            f"Learning objectives: {objectives or 'not specified'}\n"
            f"Difficulty: {difficulty}\nTime limit: {time_limit} minutes.\n"
            f"{_RESPONSE_CONTRACT}\nReturn ONLY the raw HTML."
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
