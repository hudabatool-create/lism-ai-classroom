"use client";

/**
 * Marking panel — where the teacher awards the marks no machine should.
 *
 * Grouped by stage rather than by student on purpose: marking thirty answers
 * to the same question is far faster than opening thirty students and jumping
 * between questions, because the teacher holds one mark scheme in their head
 * and works down the column.
 *
 * Deliberately not part of the live classroom. During the lesson the teacher
 * is teaching, and the same screen is being used to discuss answers with the
 * class; typing marks into a grid at that moment competes with both.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { SessionMarks, StageScore } from "@/lib/types";

export default function MarkingPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;

  const [data, setData] = useState<SessionMarks | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeStageId, setActiveStageId] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  function load() {
    api
      .get<SessionMarks>(`/api/sessions/${sessionId}/marks`)
      .then((d) => {
        setData(d);
        setActiveStageId((current) => current ?? d.stages[0]?.id ?? null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load marks"))
      .finally(() => setLoading(false));
  }

  useEffect(load, [sessionId]);

  const activeStage = data?.stages.find((s) => s.id === activeStageId) ?? null;

  // One row per student for the stage being marked, carrying their answer and
  // whatever the activity already scored.
  const rows = useMemo(() => {
    if (!data || !activeStage) return [];
    return data.students.map((student) => {
      const stage = student.stages.find((s) => s.stage_id === activeStage.id);
      return { student, stage };
    });
  }, [data, activeStage]);

  const key = (studentId: string) => `${activeStage?.id}:${studentId}`;

  async function save(studentId: string, raw: string) {
    if (!activeStage) return;
    const k = key(studentId);
    const trimmed = raw.trim();
    // An emptied box means "undo this mark", not "award zero" — the teacher
    // needs a way back after marking the wrong row.
    const mark = trimmed === "" ? null : Number(trimmed);
    if (mark !== null && (Number.isNaN(mark) || mark < 0 || mark > activeStage.marks)) {
      setError(`Enter a mark between 0 and ${activeStage.marks}`);
      return;
    }
    setSaving(k);
    setError(null);
    try {
      await api.post(`/api/sessions/${sessionId}/grade`, {
        student_id: studentId,
        stage_id: activeStage.id,
        mark,
      });
      setSaved(k);
      setTimeout(() => setSaved((s) => (s === k ? null : s)), 1500);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save that mark");
    } finally {
      setSaving(null);
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Loading marks...</p>;
  if (!data) return <p className="text-sm text-red-600">{error ?? "Could not load this session."}</p>;

  if (data.stages.length === 0) {
    return (
      <div className="max-w-2xl">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Marking</h1>
        <p className="mt-3 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
          This activity doesn&apos;t award marks, so there&apos;s nothing to grade. You can still see everything
          students wrote in the exported report.
        </p>
        <Link href="/dashboard/reports" className="mt-4 inline-block text-sm text-brand-600 hover:underline">
          Back to Reports
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Marking</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {data.activity_title} &middot; code <span className="font-mono">{data.session_code}</span> &middot; out of{" "}
            {data.total_marks}
          </p>
        </div>
        <Link
          href="/dashboard/reports"
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Back to Reports
        </Link>
      </div>

      <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
        {data.awaiting_review === 0
          ? "Every student is fully marked."
          : `${data.awaiting_review} of ${data.students.length} students still need review.`}{" "}
        A blank mark stays blank in the exported report &mdash; it never becomes a zero.
      </p>

      <div className="mt-5 flex flex-wrap gap-2">
        {data.stages.map((stage) => (
          <button
            key={stage.id}
            onClick={() => setActiveStageId(stage.id)}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
              stage.id === activeStageId
                ? "border-brand-600 bg-brand-600 text-white"
                : "border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            }`}
          >
            {stage.label} /{stage.marks}
            {stage.teacher_marks === 0 && " (auto)"}
          </button>
        ))}
      </div>

      {activeStage && activeStage.rubric.length > 0 && (
        <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Mark scheme</p>
          <ul className="mt-2 space-y-1">
            {activeStage.rubric.map((c) => (
              <li key={c.label} className="text-sm text-slate-600 dark:text-slate-300">
                <span className="font-medium text-slate-900 dark:text-white">
                  {c.label} ({c.marks})
                </span>
                {c.descriptor && <> &mdash; {c.descriptor}</>}
                {c.objective && <span className="ml-2 text-xs text-slate-400">marked automatically</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && (
        <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
          {error}
        </p>
      )}

      <div className="mt-4 overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 dark:bg-slate-900 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3">Student</th>
              <th className="px-4 py-3">Their answer</th>
              <th className="px-4 py-3">Auto</th>
              <th className="px-4 py-3 w-32">Mark /{activeStage?.marks}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {rows.map(({ student, stage }) => {
              const k = key(student.student_id);
              const draft = drafts[k];
              const stored = stage?.teacher_awarded;
              const value = draft !== undefined ? draft : stored === null || stored === undefined ? "" : String(stored);
              return (
                <tr key={student.student_id} className="align-top">
                  <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{student.name}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                    {stage?.answered ? (
                      stage.answer || <span className="text-slate-400">(submitted, no text)</span>
                    ) : (
                      <span className="text-amber-600 dark:text-amber-400">Didn&apos;t answer this</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {stage?.auto_awarded === null || stage?.auto_awarded === undefined
                      ? "—"
                      : `${stage.auto_awarded}`}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min={0}
                        max={activeStage?.marks}
                        step="0.5"
                        value={value}
                        onChange={(e) => setDrafts((d) => ({ ...d, [k]: e.target.value }))}
                        onBlur={(e) => save(student.student_id, e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                        }}
                        className="w-20 rounded-lg border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
                        placeholder="&mdash;"
                      />
                      {saving === k && <span className="text-xs text-slate-400">Saving</span>}
                      {saved === k && <span className="text-xs text-green-600">Saved</span>}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 dark:bg-slate-900 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3">Student</th>
              {data.stages.map((s) => (
                <th key={s.id} className="px-4 py-3">
                  {s.label} /{s.marks}
                </th>
              ))}
              <th className="px-4 py-3">Total</th>
              <th className="px-4 py-3">Pending</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {data.students.map((student) => (
              <tr key={student.student_id}>
                <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{student.name}</td>
                {data.stages.map((s) => {
                  const stage = student.stages.find((b) => b.stage_id === s.id);
                  return (
                    <td key={s.id} className="px-4 py-3 text-slate-600 dark:text-slate-300">
                      {cellValue(stage)}
                    </td>
                  );
                })}
                <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                  {student.awarded_total ?? "—"} / {student.max_score ?? "—"}
                </td>
                <td className="px-4 py-3">
                  {student.fully_graded ? (
                    <span className="text-green-600">Done</span>
                  ) : (
                    <span className="text-amber-600 dark:text-amber-400">{student.pending_review} marks</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Em dash for anything nobody has marked — never a zero standing in for a blank. */
function cellValue(stage: StageScore | undefined): string {
  if (!stage || stage.awarded === null || stage.awarded === undefined) return "—";
  return String(stage.awarded);
}
