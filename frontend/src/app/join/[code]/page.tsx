"use client";

import { useParams } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Logo from "@/components/Logo";
import { api } from "@/lib/api";
import { installLockstep, type LockstepHandle } from "@/lib/lockstep";
import { playTimerSound, type TimerSound } from "@/lib/timerSound";
import type { LessonManifest, SessionType, Stage } from "@/lib/types";

// Scoped per session code so a shared classroom device doesn't carry one
// lesson's identity into the next.
const studentKey = (code: string) => `lism_student_${code.toUpperCase()}`;

/** The teacher's countdown, mirrored on the student's screen.
 *
 * Derived entirely from server-supplied timing (when the stage started and
 * how long it runs), never from a locally started clock -- so a student who
 * refreshes mid-stage, or joins late, immediately sees the same time as
 * everyone else instead of a fresh countdown of their own. Students have no
 * control over it: there is deliberately no way to start, stop or alter it
 * from this page.
 */
function useStageTimer(startedAt: string | null, durationSeconds: number | null, status: string) {
  const [remaining, setRemaining] = useState<number | null>(null);

  useEffect(() => {
    if (durationSeconds == null || (status !== "running" && status !== "paused")) {
      setRemaining(null);
      return;
    }
    // Paused: the server already banked the time left, so just show it.
    if (status === "paused") {
      setRemaining(Math.max(0, durationSeconds));
      return;
    }
    if (!startedAt) return;
    const endsAt = new Date(startedAt).getTime() + durationSeconds * 1000;
    const tick = () => setRemaining(Math.max(0, Math.round((endsAt - Date.now()) / 1000)));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [startedAt, durationSeconds, status]);

  return remaining;
}

function ReportTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
      <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-0.5 text-lg font-semibold text-slate-900 dark:text-white">{value}</p>
    </div>
  );
}

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60);
  if (m < 1) return "under a minute";
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

function formatClock(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface StudentReport {
  activity_title: string;
  subject: string;
  topic: string;
  student_name: string;
  completion_status: string;
  stages_completed: number;
  stages_total: number;
  stage_breakdown: {
    label: string;
    completed: boolean;
    marks: number | null;
    awarded: number | null;
    status: string;
  }[];
  estimated_score: number | null;
  max_score: number | null;
  auto_scored: number | null;
  teacher_scored: number | null;
  pending_review: number | null;
  responses_submitted: number;
  answered_correctly: number;
  auto_graded_count: number;
  help_requests: number;
  focus_warnings: number;
  time_spent_seconds: number | null;
  teacher_review_message: string;
}

interface JoinInfo {
  session: {
    code: string;
    status: string;
    session_type: SessionType;
    stage_status: "idle" | "running" | "paused" | "ended";
    stage_started_at: string | null;
    stage_duration_seconds: number | null;
    copy_paste_protection: boolean;
    focus_monitoring: boolean;
    max_warnings: number;
    timer_sound: TimerSound;
  };
  activity: { id: string; title: string; manifest: LessonManifest };
  current_stage: Stage | null;
}

export default function JoinPage() {
  const params = useParams<{ code: string }>();
  const code = params.code;
  const [info, setInfo] = useState<JoinInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [grade, setGrade] = useState("");
  const [section, setSection] = useState("");
  const [studentId, setStudentId] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [locked, setLocked] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  // Whether a stage is currently running. LISM cannot reach inside the
  // activity's iframe to disable its buttons -- it is served from a different
  // origin -- so asking the activity to behave is the only lever we have, and
  // an activity that ignores us leaves students free to click through the
  // whole lesson. Covering the iframe with our own layer is the one thing
  // that works no matter what the activity does.
  const [stageActive, setStageActive] = useState(false);
  const [reconnected, setReconnected] = useState(false);
  const [submittedCount, setSubmittedCount] = useState(0);
  const [report, setReport] = useState<StudentReport | null>(null);
  // Mirrors the teacher's clock. Seeded from the session on load so a late
  // joiner or a refresh lands mid-countdown correctly, then kept in step by
  // the stage_started / stage_paused / stage_resumed / stage_ended events.
  const [timer, setTimer] = useState<{ startedAt: string | null; duration: number | null; status: string }>({
    startedAt: null,
    duration: null,
    status: "idle",
  });
  const remainingSeconds = useStageTimer(timer.startedAt, timer.duration, timer.status);
  const [timeUp, setTimeUp] = useState(false);
  // Fires once per stage as the countdown crosses zero. Keyed on the stage
  // start so starting the next stage re-arms it, and a refresh mid-expired
  // stage doesn't replay the sound at someone who already heard it.
  const expiredForRef = useRef<string | null>(null);
  useEffect(() => {
    if (remainingSeconds !== 0 || timer.status !== "running" || !timer.startedAt) return;
    if (expiredForRef.current === timer.startedAt) return;
    expiredForRef.current = timer.startedAt;
    setTimeUp(true);
    playTimerSound(info?.session.timer_sound);
  }, [remainingSeconds, timer.status, timer.startedAt, info?.session.timer_sound]);

  // Clear the notice as soon as the teacher moves the class on.
  useEffect(() => {
    if (timer.status !== "running" || remainingSeconds === 0) return;
    setTimeUp(false);
  }, [timer.status, remainingSeconds]);
  const [helpSent, setHelpSent] = useState(false);
  const [coachOpen, setCoachOpen] = useState(false);
  const [coachMessages, setCoachMessages] = useState<{ role: "student" | "coach"; content: string }[]>([]);
  const [coachInput, setCoachInput] = useState("");
  const [coachSending, setCoachSending] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const currentStageRef = useRef<Stage | null>(null);
  const lockstepRef = useRef<LockstepHandle | null>(null);
  // Mirrors stageActive for code paths that run outside React's render,
  // where reading the state variable would give a stale value.
  const stageStartedRef = useRef(false);
  // The WebSocket handler is created before applyLockstep exists, so it
  // calls through this rather than capturing a stale closure.
  const applyLockstepRef = useRef<(() => void) | null>(null);
  const awayRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get<JoinInfo>(`/api/join/${code}`)
      .then(async (data) => {
        if (cancelled) return;
        setInfo(data);
        currentStageRef.current = data.current_stage;
        setTimer({
          startedAt: data.session.stage_started_at,
          duration: data.session.stage_duration_seconds,
          status: data.session.stage_status,
        });
        // A student joining mid-lesson must land in the same state as everyone
        // else -- blocked if the class is between stages, not free to roam.
        stageStartedRef.current =
          data.session.stage_status === "running" || data.session.stage_status === "paused";
        setStageActive(stageStartedRef.current);

        // Reconnect silently if this device already joined this session.
        // Without this a refresh or a dropped connection sends the student
        // back to the name form, and typing a slightly different name would
        // split their work across two participants.
        const savedId = localStorage.getItem(studentKey(code));
        if (!savedId) return;
        try {
          const resumed = await api.get<{ student: { id: string }; responses: unknown[] }>(
            `/api/join/${code}/student/${savedId}`
          );
          if (cancelled) return;
          setStudentId(resumed.student.id);
          setSubmittedCount(resumed.responses.length);
          setReconnected(true);
          setTimeout(() => setReconnected(false), 4000);
        } catch {
          // Stale id (old session reusing this browser) -- fall back to the
          // join form rather than blocking the student.
          localStorage.removeItem(studentKey(code));
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Session not found");
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  async function handleJoin(e: FormEvent) {
    e.preventDefault();
    setJoining(true);
    setError(null);
    try {
      const res = await api.post<{ student: { id: string }; rejoined: boolean; responses: unknown[] }>(
        `/api/join/${code}`,
        { name, grade, section }
      );
      localStorage.setItem(studentKey(code), res.student.id);
      setStudentId(res.student.id);
      setSubmittedCount(res.responses.length);
      if (res.rejoined) {
        setReconnected(true);
        setTimeout(() => setReconnected(false), 4000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join");
    } finally {
      setJoining(false);
    }
  }

  function sendCommand(command: string, extra: Record<string, unknown> = {}) {
    iframeRef.current?.contentWindow?.postMessage({ type: "lism:command", command, ...extra }, "*");
  }

  function sendConfig(session: JoinInfo["session"]) {
    sendCommand("set_config", {
      copyPasteProtection: session.copy_paste_protection,
      focusMonitoring: session.focus_monitoring,
      maxWarnings: session.max_warnings,
    });
  }

  function handleIframeLoad() {
    // Config first: the activity should know the rules before the student can
    // interact with the stage it is about to be shown.
    if (info) sendConfig(info.session);
    if (currentStageRef.current) {
      sendCommand("start_stage", { stage: currentStageRef.current });
    }
    if (info?.session.stage_status === "paused") sendCommand("pause");

    // Then take control rather than rely on the activity having listened.
    // Served from our own origin, so the document is reachable; wrapped
    // anyway because a stray cross-origin document must not break the lesson.
    try {
      const doc = iframeRef.current?.contentDocument;
      if (doc) {
        lockstepRef.current?.destroy();
        lockstepRef.current = installLockstep(doc);
        applyLockstep();
      }
    } catch {
      /* not same-origin: fall back to the postMessage contract above */
    }
  }

  /** Point the activity at whatever stage the teacher has running. */
  const applyLockstep = useCallback(() => {
    const stage = currentStageRef.current;
    const stages = info?.activity.manifest.stages ?? [];
    const index = stage ? stages.findIndex((s) => s.id === stage.id) : -1;
    // No stage running means show nothing -- the waiting overlay covers the
    // screen anyway, but leaving a slide visible underneath invites a student
    // to read ahead through it.
    lockstepRef.current?.showStage(stageStartedRef.current ? (stage?.id ?? null) : null, index);
  }, [info]);

  useEffect(() => {
    applyLockstepRef.current = applyLockstep;
  }, [applyLockstep]);

  useEffect(() => () => lockstepRef.current?.destroy(), []);

  // The activity's response contract: prefer the new 'lism:event' shape
  // (stage-aware), but also accept the older flat 'lism-activity-response'
  // shape so activities generated before the Classroom Engine keep working.
  const handleActivityMessage = useCallback(
    (event: MessageEvent) => {
      // Paused means paused: an activity that ignores the pause command must
      // still not be able to bank answers while the class is frozen.
      if (!studentId || locked || paused) return;
      const data = event.data ?? {};
      let stageId: string | undefined;
      let correct: boolean | null = null;
      let answer = "";
      let mark: number | null = null;

      if (data.type === "lism:event" && data.event === "student_submitted") {
        stageId = data.stageId;
        correct = data.correct ?? null;
        answer = data.answer ?? "";
        mark = data.mark ?? null;
      } else if (data.type === "lism-activity-response") {
        correct = data.correct ?? null;
        answer = data.answer ?? "";
      } else {
        return;
      }

      if (!stageId) {
        stageId = currentStageRef.current?.id ?? info?.activity.manifest.stages[0]?.id;
      }

      api
        .post(`/api/join/${code}/response`, { student_id: studentId, stage_id: stageId, correct, answer, mark })
        .then(() => {
          setSubmittedCount((n) => n + 1);
          setFlash("Response submitted — your teacher can see it live.");
          setTimeout(() => setFlash(null), 3000);
        })
        .catch((err) => {
          // Show why it was rejected (already answered, session ended, locked)
          // instead of silently doing nothing, which looked like the submit
          // button was simply broken.
          setFlash(err instanceof Error ? err.message : "Could not submit your answer.");
          setTimeout(() => setFlash(null), 4000);
        });
    },
    [studentId, code, info, locked, paused]
  );

  useEffect(() => {
    window.addEventListener("message", handleActivityMessage);
    return () => window.removeEventListener("message", handleActivityMessage);
  }, [handleActivityMessage]);

  // Once joined, hold a live WebSocket connection so stage-change commands
  // from the teacher reach this device instantly.
  useEffect(() => {
    if (!studentId) return;
    const wsBase = api.base.replace(/^http/, "ws");
    const ws = new WebSocket(`${wsBase}/api/ws/session/${code}?student_id=${studentId}`);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "stage_started") {
        currentStageRef.current = msg.stage;
        setPaused(false);
        setStageActive(true);
        stageStartedRef.current = true;
        applyLockstepRef.current?.();
        setTimer({ startedAt: msg.startedAt, duration: msg.durationSeconds, status: "running" });
        sendCommand("start_stage", { stage: msg.stage });
      } else if (msg.type === "stage_ended") {
        setPaused(false);
        setStageActive(false);
        stageStartedRef.current = false;
        applyLockstepRef.current?.();
        setTimer((t) => ({ ...t, status: "ended" }));
        sendCommand("stage_ended");
      } else if (msg.type === "timer_extended") {
        setTimer((t) => ({ ...t, duration: msg.durationSeconds }));
      } else if (msg.type === "stage_paused") {
        // The overlay is what actually stops the student typing; the command
        // lets the activity freeze itself too, so a keyboard-focused input
        // inside the iframe can't keep accepting input behind the overlay.
        setPaused(true);
        setTimer((t) => ({ ...t, duration: msg.remainingSeconds, status: "paused" }));
        sendCommand("pause");
      } else if (msg.type === "stage_resumed") {
        setPaused(false);
        setTimer({ startedAt: msg.startedAt, duration: msg.durationSeconds, status: "running" });
        sendCommand("resume");
      } else if (msg.type === "session_ended") {
        setStageActive(false);
        stageStartedRef.current = false;
        // The lesson is over: show the student their report before they
        // leave, rather than leaving them on a frozen activity.
        setTimer((t) => ({ ...t, status: "ended" }));
        setPaused(false);
        api
          .get<StudentReport>(`/api/join/${code}/report/${studentId}`)
          .then((r) => setReport(r))
          .catch(() => setFlash("Your teacher ended the lesson."));
      } else if (msg.type === "settings_updated") {
        setInfo((prev) =>
          prev
            ? {
                ...prev,
                session: {
                  ...prev.session,
                  copy_paste_protection: msg.copyPasteProtection,
                  focus_monitoring: msg.focusMonitoring,
                  max_warnings: msg.maxWarnings,
                  timer_sound: msg.timerSound ?? prev.session.timer_sound,
                },
              }
            : prev
        );
        sendCommand("set_config", {
          copyPasteProtection: msg.copyPasteProtection,
          focusMonitoring: msg.focusMonitoring,
          maxWarnings: msg.maxWarnings,
        });
      }
    };

    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId, code]);

  // Focus Mode: driven by the teacher's focus_monitoring setting, which
  // defaults on for an assessment but is now switchable mid-lesson either
  // way. Detects tab switches, window switching/minimizing and leaving the
  // LISM window. blur and visibilitychange both fire for the same physical
  // "left the tab" event in most browsers, so awayRef collapses them into a
  // single violation per departure instead of double-counting.
  const focusMonitoring = info?.session.focus_monitoring ?? false;
  useEffect(() => {
    if (!studentId || !focusMonitoring || locked) return;

    async function reportViolation() {
      try {
        const res = await api.post<{ violation_number: number; locked: boolean }>(
          `/api/join/${code}/focus-violation`,
          { student_id: studentId, type: "tab_switch" }
        );
        if (res.locked) {
          setLocked(
            "This activity has been locked because you exceeded the maximum number of window exits. Your teacher has been notified."
          );
        } else if (res.violation_number === 2) {
          setWarning("Final warning: one more exit will lock this activity.");
        } else {
          setWarning("Warning: leaving this window during an assessment is being recorded.");
        }
      } catch {
        /* ignore — not critical if a single violation report fails to send */
      }
    }

    function handleAway() {
      if (awayRef.current) return;
      awayRef.current = true;
      reportViolation();
    }
    function handleBack() {
      awayRef.current = false;
    }
    function handleVisibility() {
      if (document.hidden) handleAway();
      else handleBack();
    }

    window.addEventListener("blur", handleAway);
    window.addEventListener("focus", handleBack);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      window.removeEventListener("blur", handleAway);
      window.removeEventListener("focus", handleBack);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [studentId, focusMonitoring, locked, code]);

  useEffect(() => {
    if (!warning) return;
    const timeout = setTimeout(() => setWarning(null), 5000);
    return () => clearTimeout(timeout);
  }, [warning]);

  async function handleNeedHelp() {
    if (!studentId) return;
    await api.post(`/api/join/${code}/need-help`, { student_id: studentId });
    setHelpSent(true);
    setTimeout(() => setHelpSent(false), 4000);
  }

  async function handleCoachSend(e: FormEvent) {
    e.preventDefault();
    if (!studentId || !coachInput.trim() || coachSending) return;
    const message = coachInput.trim();
    const nextHistory = [...coachMessages, { role: "student" as const, content: message }];
    setCoachMessages(nextHistory);
    setCoachInput("");
    setCoachSending(true);
    try {
      const res = await api.post<{ reply: string }>(`/api/join/${code}/coach`, {
        student_id: studentId,
        message,
        history: coachMessages,
      });
      setCoachMessages([...nextHistory, { role: "coach", content: res.reply }]);
    } finally {
      setCoachSending(false);
    }
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
        <p className="text-center text-red-600">{error}</p>
      </div>
    );
  }

  if (!info) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <p className="text-slate-400">Loading...</p>
      </div>
    );
  }

  if (info.session.status !== "active") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 text-center dark:bg-slate-950">
        <p className="text-slate-500">This session has ended.</p>
      </div>
    );
  }

  if (!studentId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
        <form
          onSubmit={handleJoin}
          className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 dark:border-slate-800 dark:bg-slate-900"
        >
          <div className="mb-6 flex justify-center">
            <Logo size="sm" />
          </div>
          <h1 className="mb-1 text-xl font-semibold text-slate-900 dark:text-white">{info.activity.title}</h1>
          <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">Enter your details to join.</p>
          {info.session.session_type === "assessment" && (
            <p className="mb-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              This is an assessment. Leaving this window will be recorded, and repeated exits will lock your
              activity.
            </p>
          )}
          <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Name</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} className="input mb-4" />
          <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Grade</label>
          <input value={grade} onChange={(e) => setGrade(e.target.value)} className="input mb-4" />
          <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Section</label>
          <input value={section} onChange={(e) => setSection(e.target.value)} className="input mb-6" />
          <button
            type="submit"
            disabled={joining}
            className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {joining ? "Joining..." : "Join Activity"}
          </button>
        </form>
      </div>
    );
  }

  const stageLabel = currentStageRef.current?.label ?? info?.current_stage?.label ?? null;
  const stageMarks = currentStageRef.current?.marks ?? info?.current_stage?.marks ?? null;

  return (
    <div className="relative flex min-h-screen flex-col bg-slate-50 dark:bg-slate-950">
      {/* The teacher's countdown, mirrored. Read-only by design -- there are
          deliberately no controls here for the student. */}
      {remainingSeconds !== null && (
        <div
          className={`flex items-center justify-center gap-3 px-4 py-2 text-sm font-medium text-white ${
            paused ? "bg-amber-500" : remainingSeconds <= 30 ? "bg-red-600" : "bg-slate-800"
          }`}
        >
          {stageLabel && <span className="opacity-90">{stageLabel}</span>}
          <span className="font-mono text-base font-semibold tabular-nums">{formatClock(remainingSeconds)}</span>
          <span className="opacity-90">
            {paused ? "paused by your teacher" : remainingSeconds === 0 ? "time's up — wait for your teacher" : "left"}
          </span>
        </div>
      )}
      {/* Tells students this section counts, without promising a number that
          might not arrive -- a teacher may choose not to mark it, and a child
          told "you will be graded" who then sees nothing stops believing it. */}
      {stageMarks !== null && stageMarks > 0 && !report && (
        <div className="bg-brand-600 px-4 py-2 text-center text-sm font-medium text-white">
          {stageMarks} mark{stageMarks === 1 ? "" : "s"} &mdash; your teacher will see and review this
        </div>
      )}
      {timeUp && !report && (
        <div className="bg-red-600 px-4 py-3 text-center text-base font-semibold text-white">
          ⏰ Time&apos;s Up! Please stop working and wait for your teacher&apos;s instructions.
        </div>
      )}
      {reconnected && (
        <div className="bg-brand-600 px-4 py-2 text-center text-sm font-medium text-white">
          Welcome back &mdash; you&apos;re back in the same lesson
          {submittedCount > 0 && `, with your ${submittedCount} answer${submittedCount === 1 ? "" : "s"} saved`}.
        </div>
      )}
      {flash && <div className="bg-green-600 px-4 py-2 text-center text-sm font-medium text-white">{flash}</div>}
      {warning && !locked && (
        <div className="bg-amber-500 px-4 py-2 text-center text-sm font-semibold text-white">{warning}</div>
      )}

      <iframe
        ref={iframeRef}
        onLoad={handleIframeLoad}
        title={info.activity.title}
        // Served through LISM's own origin so lockstep can reach the
        // document. Pointing straight at the backend would make this
        // cross-origin and leave us unable to enforce anything.
        src={`/activity/${info.activity.id}/raw`}
        className="flex-1 border-0"
      />

      {/* A strip of our own, below the activity rather than floating over it.
          These used to sit on top of the iframe's bottom-right corner, which
          is exactly where an activity puts its own controls -- students
          reported the buttons being unreachable underneath ours. Giving them
          their own row means they can never cover the activity, whatever it
          decides to draw down there. */}
      {!locked && !coachOpen && (
        <div className="flex shrink-0 items-center justify-end gap-2 border-t border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-900">
          <button
            onClick={handleNeedHelp}
            className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600"
          >
            {helpSent ? "Your teacher has been notified" : "Need help?"}
          </button>
          <button
            onClick={() => setCoachOpen(true)}
            className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-brand-700"
          >
            AI Learning Coach
          </button>
        </div>
      )}

      {!locked && coachOpen && (
        <div className="fixed bottom-4 right-4 flex h-[28rem] w-80 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center justify-between bg-brand-600 px-4 py-3">
            <p className="text-sm font-semibold text-white">AI Learning Coach</p>
            <button onClick={() => setCoachOpen(false)} className="text-white/80 hover:text-white" aria-label="Close">
              ✕
            </button>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {coachMessages.length === 0 && (
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Stuck on something? Ask a question — the coach will help you think it through, not give you the
                answer.
              </p>
            )}
            {coachMessages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                  m.role === "student"
                    ? "ml-auto bg-brand-600 text-white"
                    : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                }`}
              >
                {m.content}
              </div>
            ))}
            {coachSending && <p className="text-xs text-slate-400">Coach is typing...</p>}
          </div>
          <form onSubmit={handleCoachSend} className="flex gap-2 border-t border-slate-200 p-2 dark:border-slate-700">
            <input
              value={coachInput}
              onChange={(e) => setCoachInput(e.target.value)}
              placeholder="Ask the coach..."
              className="input"
            />
            <button
              type="submit"
              disabled={coachSending}
              className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      )}

      {/* Highest layer: once the lesson is over this is the only thing that
          matters, and it should cover a paused or locked overlay. */}
      {report && (
        <div className="fixed inset-0 z-[60] overflow-y-auto bg-slate-950/95 px-4 py-8">
          <div className="mx-auto max-w-lg rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900">
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">Lesson complete</p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{report.activity_title}</h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {[report.subject, report.topic].filter(Boolean).join(" · ")}
            </p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{report.student_name}</p>

            <div className="mt-5 grid grid-cols-2 gap-3">
              <ReportTile label="Status" value={report.completion_status} />
              <ReportTile label="Sections completed" value={`${report.stages_completed} of ${report.stages_total}`} />
              <ReportTile
                // "So far" not "estimated": the number is real marks already
                // earned on the parts that mark themselves, with the rest
                // still to come from the teacher.
                label={report.pending_review ? "Marks so far" : "Your score"}
                value={
                  report.estimated_score === null
                    ? "Not scored"
                    : report.max_score
                      ? `${report.estimated_score} / ${report.max_score}`
                      : // Marks were awarded but the activity declares no total.
                        // Showing "Not scored" here would hide real work.
                        `${report.estimated_score} mark${report.estimated_score === 1 ? "" : "s"}`
                }
              />
              <ReportTile
                label="Time spent"
                value={report.time_spent_seconds !== null ? formatDuration(report.time_spent_seconds) : "—"}
              />
            </div>

            <div className="mt-5">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">Your sections</p>
              <ul className="mt-2 space-y-1">
                {report.stage_breakdown.map((s) => (
                  <li key={s.label} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <span className={s.completed ? "text-green-600" : "text-slate-400"}>{s.completed ? "✓" : "○"}</span>
                    <span className="flex-1">{s.label}</span>
                    {s.marks !== null && (
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {s.status === "pending_review" || s.status === "not_answered"
                          ? // Never show a number here as if it were final --
                            // the teacher hasn't looked at it yet.
                            `with your teacher · ${s.marks}`
                          : `${s.awarded ?? "—"} / ${s.marks}`}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-5">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">Participation</p>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                {report.responses_submitted} answer{report.responses_submitted === 1 ? "" : "s"} submitted
                {report.auto_graded_count > 0 &&
                  ` · ${report.answered_correctly} of ${report.auto_graded_count} correct so far`}
                {report.help_requests > 0 && ` · asked for help ${report.help_requests}×`}
                {report.focus_warnings > 0 && ` · ${report.focus_warnings} focus warning${report.focus_warnings === 1 ? "" : "s"}`}
              </p>
            </div>

            <p className="mt-5 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              {report.teacher_review_message}
            </p>
          </div>
        </div>
      )}

      {/* Between stages -- and before the first one -- the activity is covered
          entirely. This is the only enforcement that holds: the iframe is a
          different origin, so LISM cannot disable an activity's own Next
          button, and an activity that ignores start_stage would otherwise let
          a student read and answer the whole lesson before the teacher has
          begun. Sits under paused and locked so a stricter state always wins. */}
      {!stageActive && !paused && !locked && !report && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-950/95 px-6 text-center">
          <div className="max-w-md">
            <Logo size="sm" />
            <p className="mt-6 text-lg font-semibold text-white">Waiting for your teacher</p>
            <p className="mt-3 text-sm text-slate-300">
              {timer.status === "ended"
                ? "That section is finished. Your teacher will start the next one shortly."
                : "The lesson will appear here as soon as your teacher starts the first section."}
            </p>
            <p className="mt-4 text-xs text-slate-500">
              You&apos;re connected. Nothing else to do — just wait.
            </p>
          </div>
        </div>
      )}

      {/* Paused sits below the lock overlay's z-index on purpose: a locked
          student stays locked even if the teacher pauses the class. */}
      {paused && !locked && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/90 px-6 text-center">
          <div className="max-w-md">
            <p className="text-lg font-semibold text-white">Paused by your teacher</p>
            <p className="mt-3 text-sm text-slate-300">
              Your work is saved. You&apos;ll be able to carry on as soon as your teacher resumes the lesson.
            </p>
          </div>
        </div>
      )}

      {locked && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/95 px-6 text-center">
          <div className="max-w-md">
            <p className="text-lg font-semibold text-white">Activity locked</p>
            <p className="mt-3 text-sm text-slate-300">{locked}</p>
          </div>
        </div>
      )}
    </div>
  );
}
