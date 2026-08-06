"use client";

import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import StagePreview from "@/components/StagePreview";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import { playTimerSound, TIMER_SOUND_OPTIONS, type TimerSound } from "@/lib/timerSound";
import type {
  Activity,
  FocusViolation,
  ResponseItem,
  SessionInfo,
  Stage,
  Student,
  StudentStatus,
  StudentStatusValue,
} from "@/lib/types";

function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <button
      onClick={handleCopy}
      className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
    >
      {copied ? "Copied!" : label}
    </button>
  );
}

function formatSeconds(total: number | null) {
  if (total == null) return "0:00";
  const m = Math.floor(Math.max(0, total) / 60);
  const s = Math.max(0, total) % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function SettingToggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-3">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 shrink-0 accent-brand-600"
      />
      <span>
        <span className="block text-sm font-medium text-slate-800 dark:text-slate-200">{label}</span>
        <span className="block text-xs text-slate-500 dark:text-slate-400">{hint}</span>
      </span>
    </label>
  );
}

function useCountdown(startedAt: string | null, durationSeconds: number | null, running: boolean) {
  const [remaining, setRemaining] = useState<number | null>(null);

  useEffect(() => {
    if (!running || !startedAt || durationSeconds == null) {
      setRemaining(null);
      return;
    }
    const endsAt = new Date(startedAt).getTime() + durationSeconds * 1000;
    const tick = () => setRemaining(Math.max(0, Math.round((endsAt - Date.now()) / 1000)));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [startedAt, durationSeconds, running]);

  if (remaining == null) return null;
  const m = Math.floor(remaining / 60);
  const s = remaining % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const STATUS_LABELS: Record<StudentStatusValue, string> = {
  working: "Working",
  completed: "Completed",
  waiting: "Waiting",
  needs_help: "Needs Help",
  inactive: "Inactive",
  locked: "Locked",
};

const STATUS_BADGE_CLASSES: Record<StudentStatusValue, string> = {
  working: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  completed: "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400",
  waiting: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  needs_help: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  inactive: "bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500",
  locked: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400",
};

const SESSION_TYPE_LABELS: Record<string, string> = {
  lesson: "Lesson Mode",
  practice: "Practice Mode",
  assessment: "Assessment Mode (Focus Mode on)",
};

interface SessionDetail {
  session: SessionInfo;
  activity: Activity;
  students: Student[];
  responses: ResponseItem[];
  current_stage: Stage | null;
  student_statuses: Record<string, StudentStatus>;
  status_summary: Record<string, number>;
  focus_violations: FocusViolation[];
}

export default function LiveSessionPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [ending, setEnding] = useState(false);
  const [stageActionPending, setStageActionPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoadError(null);
    api
      .get<SessionDetail>(`/api/sessions/${sessionId}`)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      // Without this the page sat on "Loading session..." forever whenever
      // the request failed, with nothing on screen explaining why.
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : "Could not load this session");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    if (!detail) return;
    const wsBase = api.base.replace(/^http/, "ws");
    // The backend requires the teacher's own JWT to open this connection --
    // otherwise anyone who knew the session code could silently watch the
    // live feed with no proof they're the teacher who owns it. The browser
    // attaches the httpOnly session cookie to this handshake automatically.
    const ws = new WebSocket(`${wsBase}/api/ws/session/${detail.session.code}`);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      setDetail((prev) => {
        if (!prev) return prev;
        if (msg.type === "student_joined") {
          return { ...prev, students: [...prev.students, msg.student] };
        }
        if (msg.type === "response_submitted") {
          return { ...prev, responses: [...prev.responses, msg.response] };
        }
        if (msg.type === "stage_started") {
          return {
            ...prev,
            current_stage: msg.stage,
            session: {
              ...prev.session,
              current_stage_index: msg.stageIndex,
              stage_status: "running",
              stage_started_at: msg.startedAt,
              stage_duration_seconds: msg.durationSeconds,
            },
          };
        }
        if (msg.type === "stage_ended") {
          return { ...prev, session: { ...prev.session, stage_status: "ended" } };
        }
        if (msg.type === "stage_paused") {
          return {
            ...prev,
            session: {
              ...prev.session,
              stage_status: "paused",
              stage_duration_seconds: msg.remainingSeconds,
            },
          };
        }
        if (msg.type === "stage_resumed") {
          return {
            ...prev,
            session: {
              ...prev.session,
              stage_status: "running",
              stage_started_at: msg.startedAt,
              stage_duration_seconds: msg.durationSeconds,
            },
          };
        }
        if (msg.type === "settings_updated") {
          return {
            ...prev,
            session: {
              ...prev.session,
              copy_paste_protection: msg.copyPasteProtection,
              focus_monitoring: msg.focusMonitoring,
              max_warnings: msg.maxWarnings,
              timer_sound: msg.timerSound ?? prev.session.timer_sound,
            },
          };
        }
        if (msg.type === "timer_extended") {
          return { ...prev, session: { ...prev.session, stage_duration_seconds: msg.durationSeconds } };
        }
        if (msg.type === "status_update") {
          return { ...prev, student_statuses: msg.statuses, status_summary: msg.summary };
        }
        if (msg.type === "focus_violation") {
          return { ...prev, focus_violations: [...prev.focus_violations, msg.violation] };
        }
        return prev;
      });
    };

    return () => ws.close();
    // Only reconnect when the session code changes, not on every response.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail?.session.code]);

  const remaining = useCountdown(
    detail?.session.stage_started_at ?? null,
    detail?.session.stage_duration_seconds ?? null,
    detail?.session.stage_status === "running"
  );

  // Time's up: alert the teacher and hold. Pacing stays with them, so this
  // deliberately never advances the stage on its own -- it only prompts.
  const [timeUp, setTimeUp] = useState(false);
  const expiredForRef = useRef<string | null>(null);
  useEffect(() => {
    const s = detail?.session;
    if (!s || s.stage_status !== "running" || remaining !== "0:00" || !s.stage_started_at) return;
    if (expiredForRef.current === s.stage_started_at) return;
    expiredForRef.current = s.stage_started_at;
    setTimeUp(true);
    playTimerSound(s.timer_sound);
  }, [remaining, detail?.session]);

  useEffect(() => {
    if (detail?.session.stage_status === "running" && remaining !== "0:00") setTimeUp(false);
  }, [detail?.session.stage_status, remaining]);

  async function handleEnd() {
    if (!detail) return;
    setEnding(true);
    try {
      await api.post(`/api/sessions/${detail.session.id}/end`);
      setDetail((prev) => (prev ? { ...prev, session: { ...prev.session, status: "ended" } } : prev));
    } finally {
      setEnding(false);
    }
  }

  async function handleStartStage() {
    if (!detail) return;
    setStageActionPending(true);
    try {
      await api.post(`/api/sessions/${detail.session.id}/stage/start`);
    } finally {
      setStageActionPending(false);
    }
  }

  async function handleEndStage() {
    if (!detail) return;
    setStageActionPending(true);
    try {
      await api.post(`/api/sessions/${detail.session.id}/stage/end`);
    } finally {
      setStageActionPending(false);
    }
  }

  async function handleExtend() {
    if (!detail) return;
    await api.post(`/api/sessions/${detail.session.id}/stage/extend`, { additional_seconds: 60 });
  }

  async function handlePause() {
    if (!detail) return;
    setStageActionPending(true);
    try {
      await api.post(`/api/sessions/${detail.session.id}/stage/pause`);
    } finally {
      setStageActionPending(false);
    }
  }

  async function handleResume() {
    if (!detail) return;
    setStageActionPending(true);
    try {
      await api.post(`/api/sessions/${detail.session.id}/stage/resume`);
    } finally {
      setStageActionPending(false);
    }
  }

  async function handleSetting(patch: Record<string, boolean | number | string>) {
    if (!detail) return;
    // The WebSocket broadcast updates local state, so don't set it here too.
    await api.patch(`/api/sessions/${detail.session.id}/settings`, patch);
  }

  if (loadError) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950">
        <p className="text-sm font-semibold text-red-700 dark:text-red-400">Could not load this session</p>
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">{loadError}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!detail) {
    return <p className="text-sm text-slate-500">Loading session...</p>;
  }

  const {
    session,
    activity,
    students,
    responses,
    current_stage,
    student_statuses = {},
    status_summary = {},
    focus_violations = [],
  } = detail;
  const stages = activity.manifest.stages;
  const isLastStage = session.current_stage_index >= stages.length - 1;

  /** Students in one status (or all, when omitted), each labelled with the
   *  stage they last answered and how far through they are -- a bare count
   *  tells the teacher three need help but not which three. */
  function studentsWithStatus(status?: StudentStatusValue) {
    const answeredStages = (studentId: string) =>
      new Set(responses.filter((r) => r.student_id === studentId && r.stage_id).map((r) => r.stage_id));

    return students
      .filter((s) => (status ? student_statuses[s.id]?.status === status : true))
      .map((s) => {
        const done = answeredStages(s.id);
        const percent = stages.length ? Math.round((done.size / stages.length) * 100) : 0;
        const lastAnswered = [...stages].reverse().find((st) => done.has(st.id));
        const info = student_statuses[s.id];
        return {
          id: s.id,
          name: s.name,
          detail: (
            <>
              {lastAnswered ? lastAnswered.label : "Not started"} · {percent}%
              {info?.violation_count ? ` · ${info.violation_count} focus` : ""}
              {info?.help_requests ? ` · asked for help ${info.help_requests}×` : ""}
            </>
          ),
        };
      });
  }

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{activity.title}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Session code <span className="font-mono font-semibold text-brand-600">{session.code}</span> &middot;{" "}
            <span className={session.status === "active" ? "text-green-600" : "text-slate-400"}>
              {session.status}
            </span>
            {" · "}
            <span className={session.session_type === "assessment" ? "font-medium text-amber-600" : ""}>
              {SESSION_TYPE_LABELS[session.session_type] ?? session.session_type}
            </span>
          </p>
        </div>
        {session.status === "active" && (
          <button
            onClick={handleEnd}
            disabled={ending}
            className="rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:hover:bg-red-950"
          >
            {ending ? "Ending..." : "End Session"}
          </button>
        )}
      </div>

      {session.status === "active" && (
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Lesson stages</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                The class only moves on when you say so &mdash; students never advance independently.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {remaining && (
                <span className="rounded-lg bg-brand-50 px-3 py-1.5 font-mono text-sm font-semibold text-brand-700 dark:bg-slate-800 dark:text-brand-300">
                  {remaining}
                </span>
              )}
              {/* Paused: the countdown isn't ticking, so show the banked
                  remaining time rather than nothing at all. */}
              {session.stage_status === "paused" && (
                <span className="rounded-lg bg-amber-50 px-3 py-1.5 font-mono text-sm font-semibold text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                  {formatSeconds(session.stage_duration_seconds)} paused
                </span>
              )}
              {session.stage_status === "running" && (
                <>
                  <button
                    onClick={handleExtend}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                  >
                    +1 min
                  </button>
                  <button
                    onClick={handlePause}
                    disabled={stageActionPending}
                    className="rounded-lg border border-amber-300 px-3 py-2 text-sm font-medium text-amber-700 hover:bg-amber-50 disabled:opacity-50 dark:border-amber-800 dark:text-amber-300 dark:hover:bg-amber-950"
                  >
                    Pause
                  </button>
                  <button
                    onClick={handleEndStage}
                    disabled={stageActionPending}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
                  >
                    End Stage
                  </button>
                </>
              )}
              {session.stage_status === "paused" && (
                <>
                  <button
                    onClick={handleResume}
                    disabled={stageActionPending}
                    className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
                  >
                    Resume
                  </button>
                  <button
                    onClick={handleEndStage}
                    disabled={stageActionPending}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
                  >
                    End Stage
                  </button>
                </>
              )}
              {session.stage_status !== "running" &&
                session.stage_status !== "paused" &&
                !(session.stage_status === "ended" && isLastStage) && (
                <button
                  onClick={handleStartStage}
                  disabled={stageActionPending}
                  className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  {session.current_stage_index < 0 ? "Start Stage 1" : "Start Next Stage"}
                </button>
              )}
            </div>
          </div>

          {timeUp && session.stage_status === "running" && (
            <div className="mt-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3 dark:border-red-800 dark:bg-red-950">
              <p className="text-sm font-semibold text-red-700 dark:text-red-400">
                ⏰ Time&apos;s up for {current_stage?.label ?? "this section"}
              </p>
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                Students have been told to stop and wait. Nothing has advanced &mdash; you decide when to move on.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {!isLastStage && (
                  <button
                    onClick={handleStartStage}
                    disabled={stageActionPending}
                    className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
                  >
                    Start next section
                  </button>
                )}
                <button
                  onClick={handleExtend}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                  Give them 1 more minute
                </button>
                <button
                  onClick={handleEndStage}
                  disabled={stageActionPending}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                  End this section
                </button>
              </div>
            </div>
          )}

          {session.stage_status === "paused" && (
            <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              Paused. Students can&apos;t type until you resume, and nothing they have already written is lost.
            </p>
          )}

          <ol className="mt-4 flex flex-wrap gap-2">
            {stages.map((stage, index) => {
              const isCurrent = index === session.current_stage_index;
              const isDone = index < session.current_stage_index || (isCurrent && session.stage_status === "ended" && isLastStage);
              return (
                <li
                  key={stage.id}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
                    isCurrent
                      ? "border-brand-500 bg-brand-50 text-brand-700 dark:bg-slate-800 dark:text-brand-300"
                      : isDone
                        ? "border-green-300 bg-green-50 text-green-700 dark:border-green-900 dark:bg-green-950 dark:text-green-400"
                        : "border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400"
                  }`}
                >
                  {index + 1}. {stage.label}
                  {/* The activity's own recommended duration, so the teacher
                      can see what timing the lesson was written for before
                      they start it -- and notice when a file declares nothing
                      and falls back to the 10-minute default. */}
                  {stage.durationSeconds ? (
                    <span className="ml-1.5 font-normal opacity-60">
                      {Math.round(stage.durationSeconds / 60)}m
                    </span>
                  ) : null}
                  {stage.marks ? (
                    <span className="ml-1.5 font-normal opacity-60">&middot; {stage.marks} marks</span>
                  ) : null}
                </li>
              );
            })}
          </ol>
          {session.stage_status === "ended" && isLastStage && session.current_stage_index >= 0 && (
            <p className="mt-3 text-sm font-medium text-green-600">Lesson complete &mdash; all stages finished.</p>
          )}
        </div>
      )}

      {session.status === "active" && (
        <StagePreview
          activityId={activity.id}
          stage={current_stage}
          stageIndex={session.current_stage_index}
          running={session.stage_status === "running" || session.stage_status === "paused"}
        />
      )}

      {session.status === "active" && (
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <p className="text-sm font-semibold text-slate-900 dark:text-white">Lesson settings</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Change these at any time &mdash; they apply to every student immediately, without anyone reloading.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SettingToggle
              label="Copy &amp; paste protection"
              hint="Students must type their own answers. Copy, paste and right-click are switched off inside answer boxes."
              checked={session.copy_paste_protection}
              onChange={(value) => handleSetting({ copy_paste_protection: value })}
            />
            <SettingToggle
              label="Focus monitoring"
              hint={`Records tab and window switching. Locks the activity after ${session.max_warnings} warnings and notifies you here.`}
              checked={session.focus_monitoring}
              onChange={(value) => handleSetting({ focus_monitoring: value })}
            />
            <div>
              <label
                htmlFor="timer-sound"
                className="block text-sm font-medium text-slate-800 dark:text-slate-200"
              >
                Time&apos;s-up sound
              </label>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Played on your screen and every student&apos;s when a section&apos;s timer reaches zero.
              </p>
              <div className="mt-2 flex items-center gap-2">
                <select
                  id="timer-sound"
                  value={session.timer_sound}
                  onChange={(e) => handleSetting({ timer_sound: e.target.value })}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
                >
                  {TIMER_SOUND_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => playTimerSound(session.timer_sound as TimerSound)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                  Test
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {session.status === "active" && (
        <div className="mt-6 rounded-2xl border border-brand-200 bg-brand-50 p-6 dark:border-brand-900 dark:bg-slate-900">
          <p className="text-sm font-semibold text-brand-700 dark:text-brand-300">
            Students: join this session now
          </p>
          <div className="mt-4 grid grid-cols-1 gap-6 sm:grid-cols-[auto_1fr]">
            <div className="mx-auto text-center sm:mx-0">
              {/* Dynamically generated by the backend; not a static asset, so next/image doesn't apply here. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`${api.base}/api/sessions/${session.id}/qrcode.png`}
                alt="Scan to join this session"
                className="mx-auto h-36 w-36 rounded-lg border border-slate-200 bg-white dark:border-slate-700"
              />
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Scan with a phone camera</p>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Activity code
                </p>
                <div className="mt-1 flex items-center gap-2">
                  <span className="rounded-lg bg-white px-4 py-2 font-mono text-2xl font-bold tracking-widest text-brand-700 dark:bg-slate-800 dark:text-brand-300">
                    {session.code}
                  </span>
                  <CopyButton value={session.code} label="Copy code" />
                </div>
              </div>

              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Join link
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <a
                    href={session.join_url}
                    target="_blank"
                    rel="noreferrer"
                    className="break-all text-sm font-medium text-brand-700 underline hover:text-brand-800 dark:text-brand-300"
                  >
                    {session.join_url}
                  </a>
                  {session.join_url && <CopyButton value={session.join_url} label="Copy link" />}
                </div>
              </div>

              <p className="text-xs text-slate-500 dark:text-slate-400">
                No link or camera? Students can go to{" "}
                <span className="font-medium">
                  {session.join_url ? `${new URL(session.join_url).origin}/join` : "/join"}
                </span>{" "}
                and type in the code above.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        <StatCard label="Joined" value={students.length} students={studentsWithStatus()} />
        <StatCard label="Working" value={status_summary.working ?? 0} students={studentsWithStatus("working")} />
        <StatCard
          label="Completed"
          value={status_summary.completed ?? 0}
          students={studentsWithStatus("completed")}
          tone="good"
        />
        <StatCard label="Waiting" value={status_summary.waiting ?? 0} students={studentsWithStatus("waiting")} />
        <StatCard
          label="Needs Help"
          value={status_summary.needs_help ?? 0}
          students={studentsWithStatus("needs_help")}
          tone="alert"
        />
        <StatCard label="Inactive" value={status_summary.inactive ?? 0} students={studentsWithStatus("inactive")} />
        <StatCard
          label="Locked"
          value={status_summary.locked ?? 0}
          students={studentsWithStatus("locked")}
          tone="alert"
        />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Students</h2>
          {students.length === 0 ? (
            <p className="text-sm text-slate-500">No one has joined yet.</p>
          ) : (
            <ul className="space-y-2">
              {students.map((s) => {
                const statusInfo = student_statuses[s.id];
                const status = statusInfo?.status ?? "waiting";
                return (
                  <li
                    key={s.id}
                    className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-2 text-sm dark:border-slate-800"
                  >
                    <span>
                      {s.name} {s.grade && `· Grade ${s.grade}`} {s.section && `· ${s.section}`}
                    </span>
                    <span className="flex items-center gap-2">
                      {statusInfo && statusInfo.violation_count > 0 && (
                        <span className="text-xs text-red-500">{statusInfo.violation_count}/3 exits</span>
                      )}
                      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_BADGE_CLASSES[status]}`}>
                        {STATUS_LABELS[status]}
                      </span>
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div>
          <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Live responses</h2>
          {responses.length === 0 ? (
            <p className="text-sm text-slate-500">Waiting for the first response...</p>
          ) : (
            <ul className="space-y-2">
              {[...responses].reverse().map((r) => {
                const student = students.find((s) => s.id === r.student_id);
                const stage = stages.find((s) => s.id === r.stage_id);
                return (
                  <li
                    key={r.id}
                    className="rounded-lg border border-slate-200 px-4 py-2 text-sm dark:border-slate-800"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-slate-700 dark:text-slate-200">
                        {student?.name ?? "Unknown student"}
                        {stage && <span className="ml-2 text-xs font-normal text-slate-400">&middot; {stage.label}</span>}
                      </span>
                      {r.correct !== null && (
                        <span
                          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
                            r.correct
                              ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400"
                              : "bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-400"
                          }`}
                        >
                          {r.correct ? "Correct" : "Incorrect"}
                        </span>
                      )}
                      {r.mark !== null && r.mark !== undefined && (
                        <span className="shrink-0 text-xs font-semibold text-slate-500">{r.mark} marks</span>
                      )}
                    </div>
                    {/* The answer itself, on its own line and allowed to wrap --
                        a teacher discussing feedback needs to read the whole
                        thing, not a clipped fragment squeezed beside a badge. */}
                    {r.answer ? (
                      <p className="mt-1 whitespace-pre-wrap break-words text-slate-600 dark:text-slate-300">
                        {r.answer}
                      </p>
                    ) : (
                      <p className="mt-1 text-xs italic text-slate-400">
                        This activity reported no answer text &mdash; only whether it was correct.
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      {focus_violations.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Focus report</h2>
          <ul className="space-y-2">
            {[...focus_violations].reverse().map((v) => {
              const student = students.find((s) => s.id === v.student_id);
              return (
                <li
                  key={v.id}
                  className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm dark:border-red-900 dark:bg-red-950"
                >
                  <span>
                    {student?.name ?? "Unknown student"}{" "}
                    <span className="text-xs text-red-500">&middot; exit #{v.violation_number}</span>
                  </span>
                  <span className="text-xs text-red-500">{new Date(v.occurred_at).toLocaleTimeString()}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
