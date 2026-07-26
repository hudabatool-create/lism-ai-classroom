"""Real persistence via SQLAlchemy (SQLite by default, any Postgres URL --
e.g. Supabase -- for public deployment; see DATABASE_URL in config.py).

Every method here maps onto a table in app/db/models.py and returns plain
dicts, never ORM objects -- route handlers and services never touch storage
directly, they only call through `store`, and their contracts (dict shapes,
field names) are unchanged from the in-memory version this replaced.

login_failures (login lockout counters) are intentionally kept in-memory
only, not persisted: they're a short-lived rate-limit signal, not business
data, and losing them on a restart is a harmless simplification (a fresh
lockout window is not a meaningful security regression).
"""

import copy
import random
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock

from sqlalchemy import func, select

from app.db.base import SessionLocal
from app.db.models import (
    Activity,
    ActivityAsset,
    EmailVerificationToken,
    FocusViolation,
    PasswordResetToken,
    Prompt,
    Response,
    SessionModel,
    Student,
    Teacher,
)

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


# --- Row -> dict serializers ---------------------------------------------------


def _teacher_dict(row: Teacher) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "email": row.email,
        "password_hash": row.password_hash,
        "email_verified": row.email_verified,
        "created_at": row.created_at,
    }


def _activity_dict(row: Activity) -> dict:
    return {
        "id": row.id,
        "teacher_id": row.teacher_id,
        "title": row.title,
        "subject": row.subject,
        "grade": row.grade,
        "activity_type": row.activity_type,
        "html": row.html,
        "source": row.source,
        "manifest": row.manifest,
        "assets": {a.path: a.content for a in row.assets},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _session_dict(row: SessionModel) -> dict:
    return {
        "id": row.id,
        "teacher_id": row.teacher_id,
        "activity_id": row.activity_id,
        "code": row.code,
        "status": row.status,
        "session_type": row.session_type,
        "created_at": row.created_at,
        "ended_at": row.ended_at,
        "current_stage_index": row.current_stage_index,
        "stage_status": row.stage_status,
        "stage_started_at": row.stage_started_at,
        "stage_duration_seconds": row.stage_duration_seconds,
    }


def _student_dict(row: Student) -> dict:
    return {
        "id": row.id,
        "session_id": row.session_id,
        "name": row.name,
        "grade": row.grade,
        "section": row.section,
        "joined_at": row.joined_at,
        "needs_help": row.needs_help,
        "help_requests": row.help_requests,
        "coach_messages": row.coach_messages,
    }


def _response_dict(row: Response) -> dict:
    return {
        "id": row.id,
        "session_id": row.session_id,
        "student_id": row.student_id,
        "stage_id": row.stage_id,
        "correct": row.correct,
        "answer": row.answer,
        "mark": row.mark,
        "submitted_at": row.submitted_at,
    }


def _violation_dict(row: FocusViolation) -> dict:
    return {
        "id": row.id,
        "session_id": row.session_id,
        "student_id": row.student_id,
        "type": row.type,
        "violation_number": row.violation_number,
        "occurred_at": row.occurred_at,
    }


def _prompt_dict(row: Prompt) -> dict:
    return {
        "id": row.id,
        "teacher_id": row.teacher_id,
        "title": row.title,
        "category": row.category,
        "activity_type": row.activity_type,
        "body": row.body,
        "is_favorite": row.is_favorite,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


class DataStore:
    def __init__(self):
        self._lock = Lock()
        self.login_failures: dict[str, list[datetime]] = {}

    # --- Teachers ---------------------------------------------------

    def create_teacher(self, name: str, email: str, password_hash: str) -> dict:
        with self._lock, SessionLocal() as db:
            row = Teacher(
                id=_id(),
                name=name,
                email=email,
                password_hash=password_hash,
                email_verified=False,
                created_at=_now(),
            )
            db.add(row)
            db.commit()
            return _teacher_dict(row)

    def get_teacher(self, teacher_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.get(Teacher, teacher_id)
            return _teacher_dict(row) if row else None

    def get_teacher_by_email(self, email: str) -> dict | None:
        with SessionLocal() as db:
            row = db.scalar(select(Teacher).where(Teacher.email.ilike(email)))
            return _teacher_dict(row) if row else None

    def update_teacher_password(self, teacher_id: str, password_hash: str) -> None:
        with self._lock, SessionLocal() as db:
            row = db.get(Teacher, teacher_id)
            row.password_hash = password_hash
            db.commit()

    # --- Email verification ---------------------------------------------------

    def create_email_verification_token(self, teacher_id: str) -> str:
        with self._lock, SessionLocal() as db:
            token = secrets.token_urlsafe(32)
            db.add(
                EmailVerificationToken(
                    token=token,
                    teacher_id=teacher_id,
                    expires_at=datetime.now(timezone.utc) + EMAIL_VERIFICATION_TOKEN_TTL,
                )
            )
            db.commit()
            return token

    def consume_email_verification_token(self, token: str) -> str | None:
        """Returns the teacher_id and marks the email verified, or None if the
        token doesn't exist or has expired. Single-use -- always removed."""
        with self._lock, SessionLocal() as db:
            record = db.get(EmailVerificationToken, token)
            if record is None:
                return None
            db.delete(record)
            if record.expires_at < datetime.now(timezone.utc):
                db.commit()
                return None
            teacher = db.get(Teacher, record.teacher_id)
            if teacher is None:
                db.commit()
                return None
            teacher.email_verified = True
            db.commit()
            return teacher.id

    # --- Password reset ---------------------------------------------------

    def create_password_reset_token(self, teacher_id: str) -> str:
        with self._lock, SessionLocal() as db:
            token = secrets.token_urlsafe(32)
            db.add(
                PasswordResetToken(
                    token=token,
                    teacher_id=teacher_id,
                    expires_at=datetime.now(timezone.utc) + PASSWORD_RESET_TOKEN_TTL,
                )
            )
            db.commit()
            return token

    def consume_password_reset_token(self, token: str) -> str | None:
        """Returns the teacher_id for a valid, unexpired token, or None.
        Single-use -- always removed, whether valid or not."""
        with self._lock, SessionLocal() as db:
            record = db.get(PasswordResetToken, token)
            if record is None:
                return None
            db.delete(record)
            db.commit()
            if record.expires_at < datetime.now(timezone.utc):
                return None
            return record.teacher_id

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
        with self._lock, SessionLocal() as db:
            row = Activity(
                id=_id(),
                teacher_id=teacher_id,
                title=title,
                subject=subject,
                grade=grade,
                activity_type=activity_type,
                html=html,
                source=source,
                manifest=manifest,
                created_at=_now(),
            )
            db.add(row)
            # Non-HTML files from a ZIP upload (CSS/JS/images), keyed by their
            # path relative to the entry HTML. Empty for single-file HTML
            # uploads and AI-generated activities.
            for path, content in (assets or {}).items():
                db.add(ActivityAsset(id=_id(), activity_id=row.id, path=path, content=content))
            db.commit()
            db.refresh(row)
            return _activity_dict(row)

    def list_activities(self, teacher_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(Activity).where(Activity.teacher_id == teacher_id).order_by(Activity.created_at.desc())
            )
            return [_activity_dict(r) for r in rows]

    def get_activity(self, activity_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.get(Activity, activity_id)
            return _activity_dict(row) if row else None

    def update_activity(self, activity_id: str, title: str, subject: str, grade: str, activity_type: str, html: str, manifest: dict) -> dict:
        with self._lock, SessionLocal() as db:
            row = db.get(Activity, activity_id)
            row.title = title
            row.subject = subject
            row.grade = grade
            row.activity_type = activity_type
            row.html = html
            row.manifest = manifest
            row.updated_at = _now()
            db.commit()
            db.refresh(row)
            return _activity_dict(row)

    def duplicate_activity(self, activity_id: str) -> dict:
        with self._lock, SessionLocal() as db:
            original = db.get(Activity, activity_id)
            copy_row = Activity(
                id=_id(),
                teacher_id=original.teacher_id,
                title=f"{original.title} (Copy)",
                subject=original.subject,
                grade=original.grade,
                activity_type=original.activity_type,
                html=original.html,
                source=original.source,
                manifest=copy.deepcopy(original.manifest),
                created_at=_now(),
            )
            db.add(copy_row)
            for asset in original.assets:
                db.add(ActivityAsset(id=_id(), activity_id=copy_row.id, path=asset.path, content=asset.content))
            db.commit()
            db.refresh(copy_row)
            return _activity_dict(copy_row)

    def has_sessions_for_activity(self, activity_id: str) -> bool:
        with SessionLocal() as db:
            return db.scalar(select(SessionModel.id).where(SessionModel.activity_id == activity_id)) is not None

    def delete_activity(self, activity_id: str) -> None:
        with self._lock, SessionLocal() as db:
            row = db.get(Activity, activity_id)
            if row is not None:
                db.delete(row)
                db.commit()

    # --- Sessions ---------------------------------------------------

    def create_session(self, teacher_id: str, activity_id: str, session_type: str = "lesson") -> dict:
        with self._lock, SessionLocal() as db:
            code = _gen_code()
            while db.scalar(select(SessionModel.id).where(SessionModel.code == code)) is not None:
                code = _gen_code()
            row = SessionModel(
                id=_id(),
                teacher_id=teacher_id,
                activity_id=activity_id,
                code=code,
                status="active",
                # "lesson" | "practice" | "assessment" -- only "assessment"
                # enforces Focus Mode on the student side.
                session_type=session_type,
                created_at=_now(),
                ended_at=None,
                # Classroom Engine stage state. current_stage_index == -1
                # means the lesson hasn't been started yet (teacher hasn't
                # clicked "Start Stage 1" / "Start Next Stage").
                current_stage_index=-1,
                stage_status="idle",  # "idle" | "running" | "ended"
                stage_started_at=None,
                stage_duration_seconds=None,
            )
            db.add(row)
            db.commit()
            return _session_dict(row)

    def get_session(self, session_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            return _session_dict(row) if row else None

    def get_session_by_code(self, code: str) -> dict | None:
        with SessionLocal() as db:
            row = db.scalar(select(SessionModel).where(SessionModel.code == code))
            return _session_dict(row) if row else None

    def list_sessions(self, teacher_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(SessionModel).where(SessionModel.teacher_id == teacher_id).order_by(SessionModel.created_at.desc())
            )
            return [_session_dict(r) for r in rows]

    def end_session(self, session_id: str) -> dict:
        with self._lock, SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            row.status = "ended"
            row.ended_at = _now()
            db.commit()
            return _session_dict(row)

    # --- Stage engine ---------------------------------------------------

    def start_stage(self, session_id: str, stage_index: int, duration_seconds: int) -> dict:
        with self._lock, SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            row.current_stage_index = stage_index
            row.stage_status = "running"
            row.stage_started_at = _now()
            row.stage_duration_seconds = duration_seconds
            db.commit()
            return _session_dict(row)

    def end_stage(self, session_id: str) -> dict:
        with self._lock, SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            row.stage_status = "ended"
            db.commit()
            return _session_dict(row)

    def extend_stage(self, session_id: str, additional_seconds: int) -> dict:
        with self._lock, SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            row.stage_duration_seconds = (row.stage_duration_seconds or 0) + additional_seconds
            db.commit()
            return _session_dict(row)

    # --- Students ---------------------------------------------------

    def add_student_to_session(self, session_id: str, name: str, grade: str, section: str) -> dict:
        with self._lock, SessionLocal() as db:
            row = Student(
                id=_id(),
                session_id=session_id,
                name=name,
                grade=grade,
                section=section,
                joined_at=_now(),
                needs_help=False,
                help_requests=0,
                coach_messages=0,
            )
            db.add(row)
            db.commit()
            return _student_dict(row)

    def list_students(self, session_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.scalars(select(Student).where(Student.session_id == session_id).order_by(Student.joined_at))
            return [_student_dict(r) for r in rows]

    def get_student(self, student_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.get(Student, student_id)
            return _student_dict(row) if row else None

    def get_student_in_session(self, student_id: str, session_id: str) -> dict | None:
        """Like get_student, but also verifies the student actually belongs
        to this session -- a student_id observed in one session (e.g. via a
        WebSocket broadcast) must not be usable to act as a student in a
        different session."""
        with SessionLocal() as db:
            row = db.get(Student, student_id)
            if row and row.session_id == session_id:
                return _student_dict(row)
            return None

    def increment_coach_messages(self, student_id: str) -> int | None:
        with self._lock, SessionLocal() as db:
            row = db.get(Student, student_id)
            if row is None:
                return None
            row.coach_messages += 1
            db.commit()
            return row.coach_messages

    def set_needs_help(self, student_id: str, value: bool) -> dict | None:
        with self._lock, SessionLocal() as db:
            row = db.get(Student, student_id)
            if row is None:
                return None
            row.needs_help = value
            if value:
                row.help_requests += 1
            db.commit()
            return _student_dict(row)

    # --- Focus Mode ---------------------------------------------------

    def add_focus_violation(self, session_id: str, student_id: str, violation_type: str) -> dict:
        with self._lock, SessionLocal() as db:
            count = (
                db.scalar(
                    select(func.count(FocusViolation.id)).where(
                        FocusViolation.session_id == session_id, FocusViolation.student_id == student_id
                    )
                )
                + 1
            )
            row = FocusViolation(
                id=_id(),
                session_id=session_id,
                student_id=student_id,
                type=violation_type,
                violation_number=count,
                occurred_at=_now(),
            )
            db.add(row)
            db.commit()
            return _violation_dict(row)

    def get_violation_count(self, session_id: str, student_id: str) -> int:
        with SessionLocal() as db:
            return db.scalar(
                select(func.count(FocusViolation.id)).where(
                    FocusViolation.session_id == session_id, FocusViolation.student_id == student_id
                )
            )

    def get_violation_counts(self, session_id: str) -> dict[str, int]:
        """Violation counts for every student in the session, in ONE query.

        Calling get_violation_count() per student instead was the dominant
        cost of the live dashboard: every query is a separate network
        round-trip to the database, and this is recomputed after *each*
        student action (join, response, violation, help request), so the
        per-request cost grew linearly with class size.
        """
        with SessionLocal() as db:
            rows = db.execute(
                select(FocusViolation.student_id, func.count(FocusViolation.id))
                .where(FocusViolation.session_id == session_id)
                .group_by(FocusViolation.student_id)
            ).all()
            return {student_id: count for student_id, count in rows}

    def is_locked(self, session_id: str, student_id: str) -> bool:
        return self.get_violation_count(session_id, student_id) >= 3

    def list_focus_violations(self, session_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(FocusViolation).where(FocusViolation.session_id == session_id).order_by(FocusViolation.occurred_at)
            )
            return [_violation_dict(r) for r in rows]

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
        with self._lock, SessionLocal() as db:
            row = Response(
                id=_id(),
                session_id=session_id,
                student_id=student_id,
                stage_id=stage_id,
                correct=correct,
                answer=answer,
                mark=mark,
                submitted_at=_now(),
            )
            db.add(row)
            db.commit()
            return _response_dict(row)

    def list_responses(self, session_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.scalars(select(Response).where(Response.session_id == session_id).order_by(Response.submitted_at))
            return [_response_dict(r) for r in rows]

    def has_response_for_stage(self, session_id: str, student_id: str, stage_id: str) -> bool:
        """One answer per student per stage. Without this a student could
        resubmit the same stage indefinitely -- harmless-looking in a lesson,
        but it corrupts marks and reports for an assessment."""
        with SessionLocal() as db:
            return (
                db.scalar(
                    select(Response.id).where(
                        Response.session_id == session_id,
                        Response.student_id == student_id,
                        Response.stage_id == stage_id,
                    )
                )
                is not None
            )

    # --- Prompt Library (custom, teacher-owned prompts only; built-in
    # master prompts are synthesized on read in routes/prompts.py, not
    # stored here) ---------------------------------------------------

    def create_prompt(self, teacher_id: str, title: str, category: str, activity_type: str, body: str) -> dict:
        with self._lock, SessionLocal() as db:
            now = _now()
            row = Prompt(
                id=_id(),
                teacher_id=teacher_id,
                title=title,
                category=category,
                activity_type=activity_type,
                body=body,
                is_favorite=False,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            db.commit()
            return _prompt_dict(row)

    def list_prompts(self, teacher_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.scalars(select(Prompt).where(Prompt.teacher_id == teacher_id).order_by(Prompt.created_at.desc()))
            return [_prompt_dict(r) for r in rows]

    def get_prompt(self, prompt_id: str) -> dict | None:
        with SessionLocal() as db:
            row = db.get(Prompt, prompt_id)
            return _prompt_dict(row) if row else None

    def update_prompt(self, prompt_id: str, title: str, category: str, activity_type: str, body: str) -> dict:
        with self._lock, SessionLocal() as db:
            row = db.get(Prompt, prompt_id)
            row.title = title
            row.category = category
            row.activity_type = activity_type
            row.body = body
            row.updated_at = _now()
            db.commit()
            return _prompt_dict(row)

    def set_prompt_favorite(self, prompt_id: str, value: bool) -> dict:
        with self._lock, SessionLocal() as db:
            row = db.get(Prompt, prompt_id)
            row.is_favorite = value
            db.commit()
            return _prompt_dict(row)

    def delete_prompt(self, prompt_id: str) -> None:
        with self._lock, SessionLocal() as db:
            row = db.get(Prompt, prompt_id)
            if row is not None:
                db.delete(row)
                db.commit()


store = DataStore()
