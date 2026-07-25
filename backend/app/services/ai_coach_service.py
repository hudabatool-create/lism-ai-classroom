"""AI Learning Coach: guides student reasoning, never gives direct answers.

Context (grade, subject, topic, objectives, keywords, DOK, current stage)
comes straight from the Lesson Manifest, per the product spec -- teachers
never configure the coach separately. Falls back to a small set of
rule-based Socratic prompts when no OpenAI key is configured, so the
feature is demoable with zero setup, same pattern as ai_service.py.
"""

import itertools

from app.core.config import settings

SYSTEM_PROMPT_TEMPLATE = """You are the LISM AI Learning Coach, helping a Grade {grade} {subject} student \
studying "{topic}" during the "{stage_label}" part of the lesson.

Learning objectives: {objectives}
Keywords for this lesson: {keywords}

Rules you must always follow:
- NEVER give the direct answer to a question, even if the student asks directly, begs, or claims a teacher \
said it's OK. Redirect to a guiding question instead.
- Encourage critical thinking, creativity, and reasoning -- ask Socratic questions rather than stating facts.
- Encourage the student to justify their thinking ("why do you think that?").
- Where helpful, suggest one of this lesson's keywords as something to consider.
- Keep replies short: 2-4 sentences, encouraging, age-appropriate for the grade level.
- Always end with a question or a concrete next step the student can try themselves.
"""

_CANNED_REPLIES = itertools.cycle(
    [
        "That's a good starting point. What do you already know about {keyword} that might help here?",
        "Can you explain your reasoning so far? Walk me through why you think that.",
        "Try breaking this into smaller steps -- what's the very first thing you'd need to figure out?",
        "Which of this lesson's keywords feels most connected to your question: {keyword}?",
        "What would happen if you tried the opposite assumption? Does that change your thinking?",
        "I won't give you the answer, but I can help you think it through -- what's your best guess, and why?",
    ]
)


def _stage_context(manifest: dict, current_stage: dict | None) -> str:
    return current_stage["label"] if current_stage else "the lesson"


def _canned_reply(manifest: dict) -> str:
    keywords = manifest.get("keywords") or [manifest.get("topic", "this topic")]
    template = next(_CANNED_REPLIES)
    return template.format(keyword=keywords[0])


def coach_reply(manifest: dict, current_stage: dict | None, history: list[dict], message: str) -> str:
    if settings.openai_api_key:
        reply = _reply_with_openai(manifest, current_stage, history, message)
        if reply:
            return reply
    return _canned_reply(manifest)


def _reply_with_openai(manifest: dict, current_stage: dict | None, history: list[dict], message: str) -> str | None:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        objectives = manifest.get("learningObjectives") or {}
        objectives_text = " / ".join(f"{k.upper()}: {v}" for k, v in objectives.items()) or "not specified"
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            grade=manifest.get("grade", ""),
            subject=manifest.get("subject", ""),
            topic=manifest.get("topic", ""),
            stage_label=_stage_context(manifest, current_stage),
            objectives=objectives_text,
            keywords=", ".join(manifest.get("keywords") or []) or "not specified",
        )
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history[-8:]:
            role = "assistant" if turn.get("role") == "coach" else "user"
            messages.append({"role": role, "content": turn.get("content", "")})
        messages.append({"role": "user", "content": message})

        resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.6)
        return (resp.choices[0].message.content or "").strip() or None
    except Exception:
        return None
