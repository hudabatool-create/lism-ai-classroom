"use client";

import { useParams } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Logo from "@/components/Logo";
import { api } from "@/lib/api";
import type { LessonManifest, SessionType, Stage } from "@/lib/types";

interface JoinInfo {
  session: { code: string; status: string; session_type: SessionType };
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
  const [helpSent, setHelpSent] = useState(false);
  const [coachOpen, setCoachOpen] = useState(false);
  const [coachMessages, setCoachMessages] = useState<{ role: "student" | "coach"; content: string }[]>([]);
  const [coachInput, setCoachInput] = useState("");
  const [coachSending, setCoachSending] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const currentStageRef = useRef<Stage | null>(null);
  const awayRef = useRef(false);

  useEffect(() => {
    api
      .get<JoinInfo>(`/api/join/${code}`)
      .then((data) => {
        setInfo(data);
        currentStageRef.current = data.current_stage;
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Session not found"));
  }, [code]);

  async function handleJoin(e: FormEvent) {
    e.preventDefault();
    setJoining(true);
    setError(null);
    try {
      const res = await api.post<{ student: { id: string } }>(`/api/join/${code}`, { name, grade, section });
      setStudentId(res.student.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join");
    } finally {
      setJoining(false);
    }
  }

  function sendCommand(command: string, extra: Record<string, unknown> = {}) {
    iframeRef.current?.contentWindow?.postMessage({ type: "lism:command", command, ...extra }, "*");
  }

  function handleIframeLoad() {
    if (currentStageRef.current) {
      sendCommand("start_stage", { stage: currentStageRef.current });
    }
  }

  // The activity's response contract: prefer the new 'lism:event' shape
  // (stage-aware), but also accept the older flat 'lism-activity-response'
  // shape so activities generated before the Classroom Engine keep working.
  const handleActivityMessage = useCallback(
    (event: MessageEvent) => {
      if (!studentId || locked) return;
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
    [studentId, code, info, locked]
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
        sendCommand("start_stage", { stage: msg.stage });
      } else if (msg.type === "stage_ended") {
        sendCommand("stage_ended");
      }
    };

    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId, code]);

  // Focus Mode: only enforced in Assessment sessions. Detects tab switches,
  // window switching/minimizing and leaving the LISM window. blur and
  // visibilitychange both fire for the same physical "left the tab" event in
  // most browsers, so awayRef collapses them into a single violation per
  // departure instead of double-counting.
  const assessmentMode = info?.session.session_type === "assessment";
  useEffect(() => {
    if (!studentId || !assessmentMode || locked) return;

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
  }, [studentId, assessmentMode, locked, code]);

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

  return (
    <div className="relative flex min-h-screen flex-col bg-slate-50 dark:bg-slate-950">
      {flash && <div className="bg-green-600 px-4 py-2 text-center text-sm font-medium text-white">{flash}</div>}
      {warning && !locked && (
        <div className="bg-amber-500 px-4 py-2 text-center text-sm font-semibold text-white">{warning}</div>
      )}

      <iframe
        ref={iframeRef}
        onLoad={handleIframeLoad}
        title={info.activity.title}
        src={`${api.base}/api/activities/${info.activity.id}/raw`}
        className="flex-1 border-0"
      />

      {!locked && !coachOpen && (
        <div className="fixed bottom-4 right-4 flex flex-col items-end gap-2">
          <button
            onClick={() => setCoachOpen(true)}
            className="rounded-full bg-brand-600 px-4 py-3 text-sm font-semibold text-white shadow-lg hover:bg-brand-700"
          >
            AI Learning Coach
          </button>
          <button
            onClick={handleNeedHelp}
            className="rounded-full bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-lg hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600"
          >
            {helpSent ? "Your teacher has been notified" : "Need help?"}
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
