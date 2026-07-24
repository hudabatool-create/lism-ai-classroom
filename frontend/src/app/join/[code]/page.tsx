"use client";

import { useParams } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import Logo from "@/components/Logo";
import { api } from "@/lib/api";

interface JoinInfo {
  session: { code: string; status: string };
  activity: { id: string; title: string };
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
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    api
      .get<JoinInfo>(`/api/join/${code}`)
      .then(setInfo)
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

  const handleActivityMessage = useCallback(
    (event: MessageEvent) => {
      if (!studentId || event.data?.type !== "lism-activity-response") return;
      api
        .post(`/api/join/${code}/response`, {
          student_id: studentId,
          correct: event.data.correct ?? null,
          answer: event.data.answer ?? "",
        })
        .then(() => setSubmitted(true));
    },
    [studentId, code]
  );

  useEffect(() => {
    window.addEventListener("message", handleActivityMessage);
    return () => window.removeEventListener("message", handleActivityMessage);
  }, [handleActivityMessage]);

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
      {submitted && (
        <div className="bg-green-600 px-4 py-2 text-center text-sm font-medium text-white">
          Response submitted &mdash; your teacher can see it live.
        </div>
      )}
      <iframe title={info.activity.title} src={`${api.base}/api/activities/${info.activity.id}/raw`} className="flex-1 border-0" />
    </div>
  );
}
