"""In-memory data store standing in for Supabase/Postgres.

Every method here maps onto a table in db/supabase_schema.sql. Swapping this
for a real Supabase-backed store later means reimplementing this class with
the same method signatures — route handlers and services never touch storage
directly, they only call through `store`.
"""

import copy
import random
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock

LOGIN_LOCKOUT_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_WINDOW = timedelta(minutes=15)

EMAIL_VERIFICATION_TOKEN_TTL = timedelta(days=1)
PASSWORD_RESET_TOKEN_TTL = timedelta(hours=1)


def _id() -> str:
    return uuid.uuid4().hex


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


class DataStore:
    def __init__(self):
        self._lock = Lock()
        self.teachers: dict[str, dict] = {}
        self.activities: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.students: dict[str, dict] = {}
        self.responses: dict[str, dict] = {}
        self.focus_violations: dict[str, dict] = {}
        self.prompts: dict[str, dict] = {}
        self.login_failures: dict[str, list[datetime]] = {}
        self.email_verification_tokens: dict[str, dict] = {}
        self.password_reset_tokens: dict[str, dict] = {}

    # --- Teachers ---------------------------------------------------

    def create_teacher(self, name: str, email: str, password_hash: str) -> dict:
        with self._lock:
            teacher = {
                "id": _id(),
                "name": name,
                "email": email,
                "password_hash": password_hash,
                "email_verified": False,
                "created_at": _now(),
            }
            self.teachers[teacher["id"]] = teacher
            return teacher

    def get_teacher(self, teacher_id: str) -> dict | None:
        return self.teachers.get(teacher_id)

    def get_teacher_by_email(self, email: str) -> dict | None:
        return next((t for t in self.teachers.values() if t["email"].lower() == email.lower()), None)

    def update_teacher_password(self, teacher_id: str, password_hash: str) -> None:
        with self._lock:
            self.teachers[teacher_id]["password_hash"] = password_hash

    # --- Email verification ---------------------------------------------------

    def create_email_verification_token(self, teacher_id: str) -> str:
        with self._lock:
            token = secrets.token_urlsafe(32)
            self.email_verification_tokens[token] = {
                "teacher_id": teacher_id,
                "expires_at": datetime.now(timezone.utc) + EMAIL_VERIFICATION_TOKEN_TTL,
            }
            return token

    def consume_email_verification_token(self, token: str) -> str | None:
        """Returns the teacher_id and marks the email verified, or None if the
        token doesn't exist or has expired. Single-use -- always removed."""
        with self._lock:
            record = self.email_verification_tokens.pop(token, None)
            if record is None or record["expires_at"] < datetime.now(timezone.utc):
                return None
            teacher = self.teachers.get(record["teacher_id"])
            if teacher is None:
                return None
            teacher["email_verified"] = True
            return teacher["id"]

    # --- Password reset ---------------------------------------------------

    def create_password_reset_token(self, teacher_id: str) -> str:
        with self._lock:
            token = secrets.token_urlsafe(32)
            self.password_reset_tokens[token] = {
                "teacher_id": teacher_id,
                "expires_at": datetime.now(timezone.utc) + PASSWORD_RESET_TOKEN_TTL,
            }
            return token

    def consume_password_reset_token(self, token: str) -> str | None:
        """Returns the teacher_id for a valid, unexpired token, or None.
        Single-use -- always removed, whether valid or not."""
        with self._lock:
            record = self.password_reset_tokens.pop(token, None)
            if record is None or record["expires_at"] < datetime.now(timezone.utc):
                return None
            return record["teacher_id"]

    # --- Login lockout ---------------------------------------------------
    # In-memory brute-force protection: after LOGIN_LOCKOUT_MAX_ATTEMPTS
    # failed logins for an email within LOGIN_LOCKOUT_WINDOW, further
    # attempts are rejected until the window passes. Keyed on the
    # normalized email rather than IP, since this scaffold has no reliable
    # client IP (no reverse proxy config) and the account being targeted
    # is what actually matters here.

    def _prune_login_failures(self, key: str) -> list[datetime]:
        cutoff = datetime.now(timezone.utc) - LOGIN_LOCKOUT_WINDOW
        attempts = [t for t in self.login_failures.get(key, []) if t > cutoff]
        self.login_failures[key] = attempts
        return attempts

    def is_login_locked(self, email: str) -> bool:
        with self._lock:
            key = email.lower()
            return len(self._prune_login_failures(key)) >= LOGIN_LOCKOUT_MAX_ATTEMPTS

    def record_login_failure(self, email: str) -> int:
        with self._lock:
            key = email.lower()
            attempts = self._prune_login_failures(key)
            attempts.append(datetime.now(timezone.utc))
            self.login_failures[key] = attempts
            return len(attempts)

    def clear_login_failures(self, email: str) -> None:
        with self._lock:
            self.login_failures.pop(email.lower(), None)

    # --- Activities ---------------------------------------------------

    def create_activity(self, teacher_id, title, subject, grade, activity_type, html, source, manifest, assets=None) -> dict:
        with self._lock:
            activity = {
                "id": _id(),
                "teacher_id": teacher_id,
                "title": title,
                "subject": subject,
                "grade": grade,
                "activity_type": activity_type,
                "html": html,
                "source": source,
                "manifest": manifest,
                # Non-HTML files from a ZIP upload (CSS/JS/images), keyed by
                # their path relative to the entry HTML. Empty for
                # single-file HTML uploads and AI-generated activities.
                "assets": assets or {},
                "created_at": _now(),
            }
            self.activities[activity["id"]] = activity
            return activity

    def list_activities(self, teacher_id: str) -> list[dict]:
        items = [a for a in self.activities.values() if a["teacher_id"] == teacher_id]
        return sorted(items, key=lambda a: a["created_at"], reverse=True)

    def get_activity(self, activity_id: str) -> dict | None:
        return self.activities.get(activity_id)

    def update_activity(self, activity_id: str, title: str, subject: str, grade: str, activity_type: str, html: str, manifest: dict) -> dict:
        with self._lock:
            activity = self.activities[activity_id]
            activity.update(
                title=title,
                subject=subject,
                grade=grade,
                activity_type=activity_type,
                html=html,
                manifest=manifest,
                updated_at=_now(),
            )
            return activity

    def duplicate_activity(self, activity_id: str) -> dict:
        with self._lock:
            original = self.activities[activity_id]
            copy_activity = {
                **original,
                "id": _id(),
                "title": f"{original['title']} (Copy)",
                "manifest": copy.deepcopy(original["manifest"]),
                "assets": dict(original.get("assets") or {}),
                "created_at": _now(),
            }
            self.activities[copy_activity["id"]] = copy_activity
            return copy_activity

    def has_sessions_for_activity(self, activity_id: str) -> bool:
        return any(s["activity_id"] == activity_id for s in self.sessions.values())

    def delete_activity(self, activity_id: str) -> None:
        with self._lock:
            self.activities.pop(activity_id, None)

    # --- Sessions ---------------------------------------------------

    def create_session(self, teacher_id: str, activity_id: str, session_type: str = "lesson") -> dict:
        with self._lock:
            code = _gen_code()
            while any(s["code"] == code for s in self.sessions.values()):
                code = _gen_code()
            session = {
                "id": _id(),
                "teacher_id": teacher_id,
                "activity_id": activity_id,
                "code": code,
                "status": "active",
                # "lesson" | "practice" | "assessment" — only "assessment"
                # enforces Focus Mode on the student side.
                "session_type": session_type,
                "created_at": _now(),
                "ended_at": None,
                # Classroom Engine stage state. current_stage_index == -1 means
                # the lesson hasn't been started yet (teacher hasn't clicked
                # "Start Stage 1" / "Start Next Stage").
                "current_stage_index": -1,
                "stage_status": "idle",  # "idle" | "running" | "ended"
                "stage_started_at": None,
                "stage_duration_seconds": None,
            }
            self.sessions[session["id"]] = session
            return session

    def get_session(self, session_id: str) -> dict | None:
        return self.sessions.get(session_id)

    def get_session_by_code(self, code: str) -> dict | None:
        return next((s for s in self.sessions.values() if s["code"] == code), None)

    def list_sessions(self, teacher_id: str) -> list[dict]:
        items = [s for s in self.sessions.values() if s["teacher_id"] == teacher_id]
        return sorted(items, key=lambda s: s["created_at"], reverse=True)

    def end_session(self, session_id: str) -> dict:
        session = self.sessions[session_id]
        session["status"] = "ended"
        session["ended_at"] = _now()
        return session

    # --- Stage engine ---------------------------------------------------

    def start_stage(self, session_id: str, stage_index: int, duration_seconds: int) -> dict:
        with self._lock:
            session = self.sessions[session_id]
            session["current_stage_index"] = stage_index
            session["stage_status"] = "running"
            session["stage_started_at"] = _now()
            session["stage_duration_seconds"] = duration_seconds
            return session

    def end_stage(self, session_id: str) -> dict:
        with self._lock:
            session = self.sessions[session_id]
            session["stage_status"] = "ended"
            return session

    def extend_stage(self, session_id: str, additional_seconds: int) -> dict:
        with self._lock:
            session = self.sessions[session_id]
            session["stage_duration_seconds"] = (session.get("stage_duration_seconds") or 0) + additional_seconds
            return session

    # --- Students ---------------------------------------------------

    def add_student_to_session(self, session_id: str, name: str, grade: str, section: str) -> dict:
        with self._lock:
            student = {
                "id": _id(),
                "session_id": session_id,
                "name": name,
                "grade": grade,
                "section": section,
                "joined_at": _now(),
                "needs_help": False,
                "help_requests": 0,
                "coach_messages": 0,
            }
            self.students[student["id"]] = student
            return student

    def list_students(self, session_id: str) -> list[dict]:
        items = [s for s in self.students.values() if s["session_id"] == session_id]
        return sorted(items, key=lambda s: s["joined_at"])

    def get_student(self, student_id: str) -> dict | None:
        return self.students.get(student_id)

    def get_student_in_session(self, student_id: str, session_id: str) -> dict | None:
        """Like get_student, but also verifies the student actually belongs
        to this session -- a student_id observed in one session (e.g. via a
        WebSocket broadcast) must not be usable to act as a student in a
        different session."""
        student = self.students.get(student_id)
        if student and student["session_id"] == session_id:
            return student
        return None

    def increment_coach_messages(self, student_id: str) -> int | None:
        with self._lock:
            student = self.students.get(student_id)
            if student is None:
                return None
            student["coach_messages"] += 1
            return student["coach_messages"]

    def set_needs_help(self, student_id: str, value: bool) -> dict | None:
        with self._lock:
            student = self.students.get(student_id)
            if student is None:
                return None
            student["needs_help"] = value
            if value:
                student["help_requests"] += 1
            return student

    # --- Focus Mode ---------------------------------------------------

    def add_focus_violation(self, session_id: str, student_id: str, violation_type: str) -> dict:
        with self._lock:
            count = self.get_violation_count(session_id, student_id) + 1
            violation = {
                "id": _id(),
                "session_id": session_id,
                "student_id": student_id,
                "type": violation_type,
                "violation_number": count,
                "occurred_at": _now(),
            }
            self.focus_violations[violation["id"]] = violation
            return violation

    def get_violation_count(self, session_id: str, student_id: str) -> int:
        return sum(
            1
            for v in self.focus_violations.values()
            if v["session_id"] == session_id and v["student_id"] == student_id
        )

    def is_locked(self, session_id: str, student_id: str) -> bool:
        return self.get_violation_count(session_id, student_id) >= 3

    def list_focus_violations(self, session_id: str) -> list[dict]:
        items = [v for v in self.focus_violations.values() if v["session_id"] == session_id]
        return sorted(items, key=lambda v: v["occurred_at"])

    # --- Responses ---------------------------------------------------

    def add_response(
        self,
        session_id: str,
        student_id: str,
        stage_id: str,
        correct: bool | None,
        answer: str,
        mark: float | None = None,
    ) -> dict:
        with self._lock:
            response = {
                "id": _id(),
                "session_id": session_id,
                "student_id": student_id,
                "stage_id": stage_id,
                "correct": correct,
                "answer": answer,
                "mark": mark,
                "submitted_at": _now(),
            }
            self.responses[response["id"]] = response
            return response

    def list_responses(self, session_id: str) -> list[dict]:
        items = [r for r in self.responses.values() if r["session_id"] == session_id]
        return sorted(items, key=lambda r: r["submitted_at"])

    # --- Prompt Library (custom, teacher-owned prompts only; built-in
    # master prompts are synthesized on read in routes/prompts.py, not
    # stored here) ---------------------------------------------------

    def create_prompt(self, teacher_id: str, title: str, category: str, activity_type: str, body: str) -> dict:
        with self._lock:
            prompt = {
                "id": _id(),
                "teacher_id": teacher_id,
                "title": title,
                "category": category,
                "activity_type": activity_type,
                "body": body,
                "is_favorite": False,
                "created_at": _now(),
                "updated_at": _now(),
            }
            self.prompts[prompt["id"]] = prompt
            return prompt

    def list_prompts(self, teacher_id: str) -> list[dict]:
        items = [p for p in self.prompts.values() if p["teacher_id"] == teacher_id]
        return sorted(items, key=lambda p: p["created_at"], reverse=True)

    def get_prompt(self, prompt_id: str) -> dict | None:
        return self.prompts.get(prompt_id)

    def update_prompt(self, prompt_id: str, title: str, category: str, activity_type: str, body: str) -> dict:
        with self._lock:
            prompt = self.prompts[prompt_id]
            prompt.update(title=title, category=category, activity_type=activity_type, body=body, updated_at=_now())
            return prompt

    def set_prompt_favorite(self, prompt_id: str, value: bool) -> dict:
        with self._lock:
            prompt = self.prompts[prompt_id]
            prompt["is_favorite"] = value
            return prompt

    def delete_prompt(self, prompt_id: str) -> None:
        with self._lock:
            self.prompts.pop(prompt_id, None)


store = DataStore()
