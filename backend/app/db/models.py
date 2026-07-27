"""ORM models. Mirrors the shape data_store.py used to keep in plain dicts --
timestamps stay ISO-format strings (not native datetime columns) so sorting
and JSON serialization behave exactly as before; only manifest (JSON) and
asset bytes (BLOB) get real typed columns.
"""

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, default="")
    grade: Mapped[str] = mapped_column(String, default="")
    activity_type: Mapped[str] = mapped_column(String, default="")
    html: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="upload")
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str | None] = mapped_column(String, nullable=True)

    assets: Mapped[list["ActivityAsset"]] = relationship(cascade="all, delete-orphan")


class ActivityAsset(Base):
    __tablename__ = "activity_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    session_type: Mapped[str] = mapped_column(String, nullable=False, default="lesson")
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    ended_at: Mapped[str | None] = mapped_column(String, nullable=True)
    current_stage_index: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    # "idle" | "running" | "paused" | "ended"
    stage_status: Mapped[str] = mapped_column(String, nullable=False, default="idle")
    stage_started_at: Mapped[str | None] = mapped_column(String, nullable=True)
    # While running this is the time left from stage_started_at. Pausing
    # rewrites it to the remaining seconds and resuming restarts the clock
    # from now, so the countdown maths is identical in both states.
    stage_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Teacher-controlled per-session settings, delivered to the activity as a
    # lism:command set_config (see docs/LISM_ACTIVITY_CONTRACT.md).
    copy_paste_protection: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    focus_monitoring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_warnings: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # "none" | "chime" | "bell" | "school_bell" -- played on both teacher and
    # student screens when a stage timer reaches zero.
    timer_sound: Mapped[str] = mapped_column(String, nullable=False, default="chime")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    grade: Mapped[str] = mapped_column(String, default="")
    section: Mapped[str] = mapped_column(String, default="")
    joined_at: Mapped[str] = mapped_column(String, nullable=False)
    needs_help: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    help_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coach_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_id: Mapped[str | None] = mapped_column(String, nullable=True)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    answer: Mapped[str] = mapped_column(Text, default="")
    mark: Mapped[float | None] = mapped_column(Float, nullable=True)
    submitted_at: Mapped[str] = mapped_column(String, nullable=False)


class FocusViolation(Base):
    __tablename__ = "focus_violations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    violation_number: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[str] = mapped_column(String, nullable=False)


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, default="")
    activity_type: Mapped[str] = mapped_column(String, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
