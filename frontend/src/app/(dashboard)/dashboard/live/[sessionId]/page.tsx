"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import type { Activity, ResponseItem, SessionInfo, Stage, Student } from "@/lib/types";

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

interface SessionDetail {
  session: SessionInfo;
  activity: Activity;
  students: Student[];
  responses: ResponseItem[];
  current_stage: Stage | null;
}

export default function LiveSessionPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [ending, setEnding] = useState(false);
  const [stageActionPending, setStageActionPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.get<SessionDetail>(`/api/sessions/${sessionId}`).then((d) => {
      if (!cancelled) setDetail(d);
    });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    if (!detail) return;
    const wsBase = api.base.replace(/^http/, "ws");
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
        if (msg.type === "timer_extended") {
          return { ...prev, session: { ...prev.session, stage_duration_seconds: msg.durationSeconds } };
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

  if (!detail) {
    return <p className="text-sm text-slate-500">Loading session...</p>;
  }

  const { session, activity, students, responses, current_stage } = detail;
  const stages = activity.manifest.stages;
  const isLastStage = session.current_stage_index >= stages.length - 1;
  const stageResponses = current_stage ? responses.filter((r) => r.stage_id === current_stage.id) : [];
  const completionRate = students.length ? Math.round((stageResponses.length / students.length) * 100) : 0;

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
              {session.stage_status === "running" && (
                <>
                  <button
                    onClick={handleExtend}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                  >
                    +1 min
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
              {session.stage_status !== "running" && !(session.stage_status === "ended" && isLastStage) && (
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

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Students Joined" value={students.length} />
        <StatCard label={current_stage ? `Responses (${current_stage.label})` : "Responses"} value={stageResponses.length} />
        <StatCard label="Completion" value={`${completionRate}%`} />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Students</h2>
          {students.length === 0 ? (
            <p className="text-sm text-slate-500">No one has joined yet.</p>
          ) : (
            <ul className="space-y-2">
              {students.map((s) => (
                <li key={s.id} className="rounded-lg border border-slate-200 px-4 py-2 text-sm dark:border-slate-800">
                  {s.name} {s.grade && `· Grade ${s.grade}`} {s.section && `· ${s.section}`}
                </li>
              ))}
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
                    className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-2 text-sm dark:border-slate-800"
                  >
                    <span>
                      {student?.name ?? "Unknown student"}
                      {stage && <span className="ml-2 text-xs text-slate-400">&middot; {stage.label}</span>}
                    </span>
                    <span
                      className={
                        r.correct ? "text-green-600" : r.correct === false ? "text-red-500" : "text-slate-400"
                      }
                    >
                      {r.answer || (r.correct ? "Correct" : "Incorrect")}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
