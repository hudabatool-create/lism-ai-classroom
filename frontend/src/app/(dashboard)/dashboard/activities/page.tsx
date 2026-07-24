"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Activity, SessionInfo } from "@/lib/types";

export default function ActivitiesPage() {
  const router = useRouter();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Activity[]>("/api/activities")
      .then(setActivities)
      .finally(() => setLoading(false));
  }, []);

  async function handleLaunch(activityId: string) {
    setLaunching(activityId);
    setError(null);
    try {
      const session = await api.post<SessionInfo>(`/api/activities/${activityId}/launch`);
      router.push(`/dashboard/live/${session.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not launch session");
    } finally {
      setLaunching(null);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">My Activities</h1>
        <div className="flex gap-3">
          <Link
            href="/dashboard/activities/new"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Generate with AI
          </Link>
          <Link
            href="/dashboard/activities/upload"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Upload HTML
          </Link>
        </div>
      </div>

      {error && (
        <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
          {error}
        </p>
      )}

      {loading ? (
        <p className="mt-6 text-sm text-slate-500">Loading activities...</p>
      ) : activities.length === 0 ? (
        <p className="mt-6 text-sm text-slate-500">
          No activities yet. Generate one with AI or upload an HTML file to get started.
        </p>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {activities.map((activity) => (
            <div
              key={activity.id}
              className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
            >
              <div>
                <p className="text-xs uppercase tracking-wide text-brand-600">
                  {activity.source === "ai" ? "AI Generated" : "Uploaded"}
                </p>
                <h3 className="mt-1 font-semibold text-slate-900 dark:text-white">{activity.title}</h3>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  {activity.subject || "General"} &middot; Grade {activity.grade || "-"} &middot;{" "}
                  {activity.activity_type}
                </p>
              </div>
              <div className="mt-4 flex gap-2">
                <a
                  href={`${api.base}/api/activities/${activity.id}/raw`}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  Preview
                </a>
                <button
                  onClick={() => handleLaunch(activity.id)}
                  disabled={launching === activity.id}
                  className="flex-1 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  {launching === activity.id ? "Launching..." : "Start Activity"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
