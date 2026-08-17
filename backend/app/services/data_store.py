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
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

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


def _normalize_name(name: str) -> str:
    """Identity key for a student within a session: case- and
    spacing-insensitive, so "Aisha  Khan" and "aisha khan" are one person."""
    return " ".join(name.split()).lower()


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
        "copy_paste_protection": row.copy_paste_protection,
        "focus_monitoring": row.focus_monitoring,
        "max_warnings": row.max_warnings,
        "timer_sound": row.timer_sound,
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
        "teacher_mark": row.teacher_mark,
        "teacher_feedback": row.teacher_feedback,
        "graded_at": row.graded_at,
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
        with SessionLocal() as db:
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
        with SessionLocal() as db:
            row = db.get(Teacher, teacher_id)
            row.password_hash = password_hash
            db.commit()

    # --- Email verification ---------------------------------------------------

    def create_email_verification_token(self, teacher_id: str) -> str:
        with SessionLocal() as db:
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
        with SessionLocal() as db:
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
        with SessionLocal() as db:
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
        with SessionLocal() as db:
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
        with SessionLocal() as db:
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
        with SessionLocal() as db:
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
        with SessionLocal() as db:
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

    def count_sessions_for_activity(self, activity_id: str) -> int:
        """Used to warn the teacher exactly how much history a delete discards."""
        with SessionLocal() as db:
            return db.scalar(select(func.count(SessionModel.id)).where(SessionModel.activity_id == activity_id))

    def delete_activity(self, activity_id: str) -> None:
        with SessionLocal() as db:
            row = db.get(Activity, activity_id)
            if row is not None:
                db.delete(row)
                db.commit()

    # --- Sessions ---------------------------------------------------

    def create_session(self, teacher_id: str, activity_id: str, session_type: str = "lesson") -> dict:
        with SessionLocal() as db:
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
                stage_status="idle",  # "idle" | "running" | "paused" | "ended"
                stage_started_at=None,
                stage_duration_seconds=None,
                # Focus monitoring defaults on for an assessment and off
                # otherwise -- the previous hard-wired behaviour -- but the
                # teacher can now change it either way, mid-lesson.
                copy_paste_protection=(session_type == "assessment"),
                focus_monitoring=(session_type == "assessment"),
                max_warnings=3,
                timer_sound="chime",
            )
            db.add(row)
            db.commit()
            return _session_dict(row)

    def update_session_settings(
        self,
        session_id: str,
        copy_paste_protection: bool | None = None,
        focus_monitoring: bool | None = None,
        max_warnings: int | None = None,
        timer_sound: str | None = None,
    ) -> dict:
        with SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            if copy_paste_protection is not None:
                row.copy_paste_protection = copy_paste_protection
            if focus_monitoring is not None:
                row.focus_monitoring = focus_monitoring
            if max_warnings is not None:
                row.max_warnings = max_warnings
            if timer_sound is not None:
                row.timer_sound = timer_sound
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
        with SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            row.status = "ended"
            row.ended_at = _now()
            db.commit()
            return _session_dict(row)

    # --- Stage engine ---------------------------------------------------

    def start_stage(self, session_id: str, stage_index: int, duration_seconds: int) -> dict:
        with SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            row.current_stage_index = stage_index
            row.stage_status = "running"
            row.stage_started_at = _now()
            row.stage_duration_seconds = duration_seconds
            db.commit()
            return _session_dict(row)

    def pause_stage(self, session_id: str) -> dict:
        """Freeze the countdown by banking the time left.

        stage_duration_seconds is rewritten to whatever remains, so resuming
        only has to restart the clock from now -- the "ends at started_at +
        duration" maths every client already uses stays correct in both
        states, with no separate paused-at bookkeeping to drift.
        """
        with SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            if row.stage_started_at and row.stage_duration_seconds is not None:
                started = datetime.fromisoformat(row.stage_started_at)
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                row.stage_duration_seconds = max(0, int(row.stage_duration_seconds - elapsed))
            row.stage_status = "paused"
            db.commit()
            return _session_dict(row)

    def resume_stage(self, session_id: str) -> dict:
        with SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            row.stage_started_at = _now()
            row.stage_status = "running"
            db.commit()
            return _session_dict(row)

    def end_stage(self, session_id: str) -> dict:
        with SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            row.stage_status = "ended"
            db.commit()
            return _session_dict(row)

    def extend_stage(self, session_id: str, additional_seconds: int) -> dict:
        with SessionLocal() as db:
            row = db.get(SessionModel, session_id)
            row.stage_duration_seconds = (row.stage_duration_seconds or 0) + additional_seconds
            db.commit()
            return _session_dict(row)

    # --- Students ---------------------------------------------------

    def add_student_to_session(self, session_id: str, name: str, grade: str, section: str) -> tuple[dict, bool]:
        """Find-or-create: one student is one participant for the whole lesson.

        Returns (student, rejoined). A refresh, a dropped connection, a closed
        browser or simply typing the same name again must put the student back
        into the participant they already are -- creating a second row would
        split their answers across two identities and show the teacher the
        same child twice.

        Matching is on the normalised name within this session. Two different
        children with the identical full name in one class would share a
        participant; they need to differentiate (surname or initial), which is
        the same expectation other classroom tools set.
        """
        key = _normalize_name(name)

        def lookup(db):
            return db.scalar(
                select(Student).where(Student.session_id == session_id, Student.name_key == key)
            )

        with SessionLocal() as db:
            existing = lookup(db)
            if existing is not None:
                # Keep the latest grade/section if they filled them in this time.
                if grade:
                    existing.grade = grade
                if section:
                    existing.section = section
                db.commit()
                return _student_dict(existing), True

            row = Student(
                id=_id(),
                session_id=session_id,
                name=name,
                name_key=key,
                grade=grade,
                section=section,
                joined_at=_now(),
                needs_help=False,
                help_requests=0,
                coach_messages=0,
            )
            db.add(row)
            try:
                db.commit()
            except IntegrityError:
                # Two devices for the same student hit Join in the same
                # instant and both saw no existing row. The unique index let
                # exactly one insert through; the loser reads the winner's row
                # and treats it as a rejoin, which is what actually happened.
                db.rollback()
                winner = lookup(db)
                if winner is None:
                    raise
                return _student_dict(winner), True
            return _student_dict(row), False

    def list_student_responses(self, session_id: str, student_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(Response)
                .where(Response.session_id == session_id, Response.student_id == student_id)
                .order_by(Response.submitted_at)
            )
            return [_response_dict(r) for r in rows]

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
        with SessionLocal() as db:
            row = db.get(Student, student_id)
            if row is None:
                return None
            row.coach_messages += 1
            db.commit()
            return row.coach_messages

    def set_needs_help(self, student_id: str, value: bool) -> dict | None:
        with SessionLocal() as db:
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
        with SessionLocal() as db:
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
        with SessionLocal() as db:
            forgiven = db.scalar(
                select(Student.violations_forgiven).where(Student.id == student_id)
            ) or 0
        return self.get_violation_count(session_id, student_id) - forgiven >= 3

    def forgive_violations(self, session_id: str, student_id: str) -> int:
        """Let a locked student carry on, without erasing what happened.

        Forgives everything counted so far rather than deleting it: the Focus
        Report still shows every violation, and three more lock the student
        again. Returns the number forgiven.
        """
        count = self.get_violation_count(session_id, student_id)
        with SessionLocal() as db:
            student = db.get(Student, student_id)
            if student is None or student.session_id != session_id:
                return 0
            student.violations_forgiven = count
            db.commit()
        return count

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
        *,
        replace: bool = False,
    ) -> dict:
        """Record what a student has answered for one stage of the lesson.

        A stage keeps ONE row per student, because that is what the marking
        panel, the report and the gradebook column all assume. But a stage is
        rarely one question: an Exit Ticket has five, a Main Task has four DOK
        parts, and students answer them one at a time.

        Treating the first submission as final was wrong, and hid most of the
        lesson from the teacher -- a five-question Exit Ticket showed only
        question one, and a Main Task worth ten marks showed a single line.

        So a second submission for the same stage updates the row:

        `replace` -- the caller has just read the WHOLE section, so the new
        text already contains everything the old one had. Overwrite it.

        otherwise -- the activity reported one more question of its own. Append
        the new answer, and add its marks to the running total, so four DOK
        parts arrive as four answers and ten marks rather than the last one.
        """
        with SessionLocal() as db:
            existing = db.scalar(
                select(Response).where(
                    Response.session_id == session_id,
                    Response.student_id == student_id,
                    Response.stage_id == stage_id,
                )
            )
            if existing is None:
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

            if replace:
                existing.answer = answer
                existing.correct = correct
                existing.mark = mark
            else:
                if answer and answer not in (existing.answer or ""):
                    existing.answer = f"{existing.answer}\n\n{answer}" if existing.answer else answer
                if mark is not None:
                    existing.mark = (existing.mark or 0) + mark
                # Mixed right and wrong across a stage is neither, so stop
                # claiming a single verdict for the whole stage.
                if correct is not None and existing.correct is not None and correct != existing.correct:
                    existing.correct = None
                elif existing.correct is None:
                    existing.correct = correct
            # The time of the latest work, which is what a teacher watching a
            # live feed and an inspector reading a report both mean by it.
            existing.submitted_at = _now()
            db.commit()
            return _response_dict(existing)

    def list_responses(self, session_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.scalars(select(Response).where(Response.session_id == session_id).order_by(Response.submitted_at))
            return [_response_dict(r) for r in rows]

    def set_teacher_mark(
        self,
        session_id: str,
        student_id: str,
        stage_id: str,
        mark: float | None,
        feedback: str | None = None,
    ) -> dict | None:
        """Record the teacher's mark for one student's stage.

        A mark of None clears it back to ungraded, which the teacher needs
        when they mark the wrong row -- otherwise the only way to undo is to
        leave a wrong number in the gradebook.
        """
        with SessionLocal() as db:
            row = db.scalar(
                select(Response).where(
                    Response.session_id == session_id,
                    Response.student_id == student_id,
                    Response.stage_id == stage_id,
                )
            )
            if row is None:
                return None
            row.teacher_mark = mark
            row.teacher_feedback = feedback
            row.graded_at = _now() if mark is not None else None
            db.commit()
            db.refresh(row)
            return _response_dict(row)

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
        with SessionLocal() as db:
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
        with SessionLocal() as db:
            row = db.get(Prompt, prompt_id)
            row.title = title
            row.category = category
            row.activity_type = activity_type
            row.body = body
            row.updated_at = _now()
            db.commit()
            return _prompt_dict(row)

    def set_prompt_favorite(self, prompt_id: str, value: bool) -> dict:
        with SessionLocal() as db:
            row = db.get(Prompt, prompt_id)
            row.is_favorite = value
            db.commit()
            return _prompt_dict(row)

    def delete_prompt(self, prompt_id: str) -> None:
        with SessionLocal() as db:
            row = db.get(Prompt, prompt_id)
            if row is not None:
                db.delete(row)
                db.commit()


store = DataStore()


class _AsyncStore:
    """`store`, safe to call from an `async def` endpoint.

    Every method here does blocking database I/O. Calling one directly inside
    an `async def` handler stops the event loop for the whole round trip --
    which means one student pressing Join freezes every other request on the
    server, across every class and every teacher. A sync `def` endpoint is
    fine (FastAPI already runs those in a threadpool); an `async def` one is
    not, and the routes that broadcast over WebSocket have to be async.

    This ran the server at one request at a time in production: 32 students
    joining took 90 seconds and most timed out.

    Usage inside an async endpoint:  session = await astore.get_session(id)
    """

    def __getattr__(self, name: str):
        method = getattr(store, name)

        async def in_threadpool(*args, **kwargs):
            return await run_in_threadpool(method, *args, **kwargs)

        in_threadpool.__name__ = f"async_{name}"
        return in_threadpool


astore = _AsyncStore()
