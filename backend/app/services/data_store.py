"""In-memory data store standing in for Supabase/Postgres.

Every method here maps onto a table in db/supabase_schema.sql. Swapping this
for a real Supabase-backed store later means reimplementing this class with
the same method signatures — route handlers and services never touch storage
directly, they only call through `store`.
"""

import random
import string
import uuid
from datetime import datetime, timezone
from threading import Lock


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

    # --- Teachers ---------------------------------------------------

    def create_teacher(self, name: str, email: str, password_hash: str) -> dict:
        with self._lock:
            teacher = {
                "id": _id(),
                "name": name,
                "email": email,
                "password_hash": password_hash,
                "created_at": _now(),
            }
            self.teachers[teacher["id"]] = teacher
            return teacher

    def get_teacher(self, teacher_id: str) -> dict | None:
        return self.teachers.get(teacher_id)

    def get_teacher_by_email(self, email: str) -> dict | None:
        return next((t for t in self.teachers.values() if t["email"].lower() == email.lower()), None)

    # --- Activities ---------------------------------------------------

    def create_activity(self, teacher_id, title, subject, grade, activity_type, html, source) -> dict:
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
                "created_at": _now(),
            }
            self.activities[activity["id"]] = activity
            return activity

    def list_activities(self, teacher_id: str) -> list[dict]:
        items = [a for a in self.activities.values() if a["teacher_id"] == teacher_id]
        return sorted(items, key=lambda a: a["created_at"], reverse=True)

    def get_activity(self, activity_id: str) -> dict | None:
        return self.activities.get(activity_id)

    # --- Sessions ---------------------------------------------------

    def create_session(self, teacher_id: str, activity_id: str) -> dict:
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
                "created_at": _now(),
                "ended_at": None,
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
            }
            self.students[student["id"]] = student
            return student

    def list_students(self, session_id: str) -> list[dict]:
        items = [s for s in self.students.values() if s["session_id"] == session_id]
        return sorted(items, key=lambda s: s["joined_at"])

    # --- Responses ---------------------------------------------------

    def add_response(self, session_id: str, student_id: str, correct: bool | None, answer: str) -> dict:
        with self._lock:
            response = {
                "id": _id(),
                "session_id": session_id,
                "student_id": student_id,
                "correct": correct,
                "answer": answer,
                "submitted_at": _now(),
            }
            self.responses[response["id"]] = response
            return response

    def list_responses(self, session_id: str) -> list[dict]:
        items = [r for r in self.responses.values() if r["session_id"] == session_id]
        return sorted(items, key=lambda r: r["submitted_at"])


store = DataStore()
