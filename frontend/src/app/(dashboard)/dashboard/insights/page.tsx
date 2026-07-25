"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Activity, SessionInfo } from "@/lib/types";

export default function InsightsPage() {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get<SessionInfo[]>("/api/sessions"), api.get<Activity[]>("/api/activities")])
      .then(([s, a]) => {
        setSessions(s);
        setActivities(a);
      })
      .finally(() => setLoading(false));
  }, []);

  const activityTitle = (id: string) => activities.find((a) => a.id === id)?.title ?? "Unknown activity";

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">AI Insights</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Class summaries, misconceptions, and recommendations for any session with response data.
      </p>

      {loading ? (
        <p className="mt-6 text-sm text-slate-500">Loading...</p>
      ) : sessions.length === 0 ? (
        <p className="mt-6 text-sm text-slate-500">
          Launch a session first &mdash; insights appear here once students have responded.
        </p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 dark:bg-slate-900 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3">Activity</th>
                <th className="px-4 py-3">Code</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Started</th>
                <th className="px-4 py-3 text-right">Insights</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {sessions.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-3">{activityTitle(s.activity_id)}</td>
                  <td className="px-4 py-3 font-mono">{s.code}</td>
                  <td className="px-4 py-3">
                    <span className={s.status === "active" ? "text-green-600" : "text-slate-400"}>{s.status}</span>
                  </td>
                  <td className="px-4 py-3">{new Date(s.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/dashboard/insights/${s.id}`}
                      className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
                    >
                      View Insights
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
