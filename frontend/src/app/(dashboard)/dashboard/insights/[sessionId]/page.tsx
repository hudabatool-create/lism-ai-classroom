"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import type { Insights } from "@/lib/types";

export default function SessionInsightsPage() {
  const params = useParams<{ sessionId: string }>();
  const [insights, setInsights] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Insights>(`/api/sessions/${params.sessionId}/insights`)
      .then(setInsights)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load insights"))
      .finally(() => setLoading(false));
  }, [params.sessionId]);

  if (loading) return <p className="text-sm text-slate-500">Loading insights...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!insights) return null;

  const { stats } = insights;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">AI Insights</h1>
        <span
          className={`rounded-full px-3 py-1 text-xs font-medium ${
            insights.source === "ai"
              ? "bg-brand-50 text-brand-700 dark:bg-slate-800 dark:text-brand-300"
              : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
          }`}
        >
          {insights.source === "ai" ? "AI-generated" : "Statistical summary (no AI key configured)"}
        </span>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Joined" value={stats.students_joined} />
        <StatCard label="Participation" value={`${stats.participation_rate}%`} />
        <StatCard label="Correct Rate" value={stats.correct_rate == null ? "-" : `${stats.correct_rate}%`} />
        <StatCard label="Locked (Focus)" value={stats.students_locked} />
      </div>

      <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Class Summary</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">{insights.class_summary}</p>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Misconceptions</h2>
          <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
            {insights.misconceptions.map((m, i) => (
              <li key={i} className="rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-950/40">
                {m}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Recommendations</h2>
          <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
            {insights.recommendations.map((r, i) => (
              <li key={i} className="rounded-lg bg-brand-50 px-3 py-2 dark:bg-slate-800">
                {r}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-white">Stage Performance</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500 dark:text-slate-400">
              <tr>
                <th className="py-2 pr-4">Stage</th>
                <th className="py-2 pr-4">Responses</th>
                <th className="py-2 pr-4">Correct</th>
                <th className="py-2 pr-4">Incorrect</th>
                <th className="py-2 pr-4">Completion</th>
                <th className="py-2">Most Common Wrong Answer</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {stats.per_stage.map((stage) => (
                <tr key={stage.stage_id}>
                  <td className="py-2 pr-4 font-medium text-slate-900 dark:text-white">{stage.label}</td>
                  <td className="py-2 pr-4">{stage.responses}</td>
                  <td className="py-2 pr-4 text-green-600">{stage.correct}</td>
                  <td className="py-2 pr-4 text-red-500">{stage.incorrect}</td>
                  <td className="py-2 pr-4">{stage.completion_rate}%</td>
                  <td className="py-2 text-slate-500 dark:text-slate-400">
                    {stage.most_common_wrong_answer ?? "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-white">Student Notes</h2>
        <ul className="space-y-2 text-sm">
          {insights.student_notes.map((n, i) => (
            <li key={i} className="flex justify-between rounded-lg border border-slate-100 px-3 py-2 dark:border-slate-800">
              <span className="font-medium text-slate-900 dark:text-white">{n.name}</span>
              <span className="text-slate-500 dark:text-slate-400">{n.note}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
