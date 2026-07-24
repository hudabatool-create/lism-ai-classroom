"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Activity, SessionInfo } from "@/lib/types";

export default function LiveClassroomPage() {
  const router = useRouter();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.get<Activity[]>("/api/activities"), api.get<SessionInfo[]>("/api/sessions")])
      .then(([a, s]) => {
        setActivities(a);
        setSessions(s);
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleLaunch(activityId: string) {
    setLaunching(activityId);
    try {
      const session = await api.post<SessionInfo>(`/api/activities/${activityId}/launch`);
      router.push(`/dashboard/live/${session.id}`);
    } finally {
      setLaunching(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Live Classroom</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Launch an activity to get a session code, join link, and QR code.
      </p>

      {loading ? (
        <p className="mt-6 text-sm text-slate-500">Loading...</p>
      ) : activities.length === 0 ? (
        <p className="mt-6 text-sm text-slate-500">Create an activity first, then come back here to launch it.</p>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {activities.map((a) => (
            <div
              key={a.id}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900"
            >
              <div>
                <p className="font-medium text-slate-900 dark:text-white">{a.title}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {a.subject || "General"} &middot; Grade {a.grade || "-"}
                </p>
              </div>
              <button
                onClick={() => handleLaunch(a.id)}
                disabled={launching === a.id}
                className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
              >
                {launching === a.id ? "Launching..." : "Start"}
              </button>
            </div>
          ))}
        </div>
      )}

      {sessions.length > 0 && (
        <div className="mt-10">
          <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Previous sessions</h2>
          <ul className="space-y-2">
            {sessions.map((s) => (
              <li key={s.id}>
                <Link
                  href={`/dashboard/live/${s.id}`}
                  className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3 text-sm hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"
                >
                  <span>Session {s.code}</span>
                  <span className={s.status === "active" ? "text-green-600" : "text-slate-400"}>{s.status}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
