"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import type { Activity, SessionInfo } from "@/lib/types";

export default function DashboardOverviewPage() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get<Activity[]>("/api/activities"), api.get<SessionInfo[]>("/api/sessions")])
      .then(([a, s]) => {
        setActivities(a);
        setSessions(s);
      })
      .finally(() => setLoading(false));
  }, []);

  const activeSessions = sessions.filter((s) => s.status === "active");

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Overview</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Create. Engage. Monitor. Analyze. Inspire.</p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Activities" value={loading ? "-" : activities.length} />
        <StatCard label="Sessions Run" value={loading ? "-" : sessions.length} />
        <StatCard label="Active Now" value={loading ? "-" : activeSessions.length} />
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/dashboard/activities/new"
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Generate Activity with AI
        </Link>
        <Link
          href="/dashboard/activities/upload"
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Upload HTML Activity
        </Link>
        <Link
          href="/dashboard/live"
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Launch Live Classroom
        </Link>
      </div>

      {activeSessions.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Active sessions</h2>
          <ul className="space-y-2">
            {activeSessions.map((s) => (
              <li key={s.id}>
                <Link
                  href={`/dashboard/live/${s.id}`}
                  className="block rounded-lg border border-slate-200 px-4 py-3 text-sm hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"
                >
                  Session {s.code} &middot; started {new Date(s.created_at).toLocaleTimeString()}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
