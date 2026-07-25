"use client";

import { useParams } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Logo from "@/components/Logo";
import { api } from "@/lib/api";
import type { LessonManifest, Stage } from "@/lib/types";

interface JoinInfo {
  session: { code: string; status: string };
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
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const currentStageRef = useRef<Stage | null>(null);

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
      if (!studentId) return;
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
        });
    },
    [studentId, code, info]
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
    <div className="flex min-h-screen flex-col bg-slate-50 dark:bg-slate-950">
      {flash && (
        <div className="bg-green-600 px-4 py-2 text-center text-sm font-medium text-white">{flash}</div>
      )}
      <iframe
        ref={iframeRef}
        onLoad={handleIframeLoad}
        title={info.activity.title}
        src={`${api.base}/api/activities/${info.activity.id}/raw`}
        className="flex-1 border-0"
      />
    </div>
  );
}
