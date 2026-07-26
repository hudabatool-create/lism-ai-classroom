"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Activity, SessionInfo } from "@/lib/types";

export default function ActivitiesPage() {
  const router = useRouter();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Activity[]>("/api/activities")
      .then(setActivities)
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return activities;
    return activities.filter((a) =>
      [a.title, a.subject, a.activity_type].some((field) => field.toLowerCase().includes(q))
    );
  }, [activities, search]);

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

  async function handleDuplicate(activityId: string) {
    setPending(`${activityId}-duplicate`);
    setError(null);
    try {
      const copy = await api.post<Activity>(`/api/activities/${activityId}/duplicate`);
      setActivities((prev) => [copy, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not duplicate activity");
    } finally {
      setPending(null);
    }
  }

  async function handleDelete(activityId: string) {
    if (confirmingDelete !== activityId) {
      setConfirmingDelete(activityId);
      return;
    }
    setConfirmingDelete(null);
    setPending(`${activityId}-delete`);
    setError(null);
    try {
      await api.delete(`/api/activities/${activityId}`);
      setActivities((prev) => prev.filter((a) => a.id !== activityId));
    } catch (err) {
      // 409 means the activity has session history. Rather than refusing --
      // which left teachers unable to tidy their list at all -- say exactly
      // what else would be deleted and let them decide.
      const message = err instanceof Error ? err.message : "Could not delete activity";
      if (message.includes("has been used in")) {
        if (window.confirm(`${message}\n\nDelete it anyway?`)) {
          try {
            await api.delete(`/api/activities/${activityId}?force=true`);
            setActivities((prev) => prev.filter((a) => a.id !== activityId));
            return;
          } catch (forceErr) {
            setError(forceErr instanceof Error ? forceErr.message : "Could not delete activity");
            return;
          } finally {
            setPending(null);
          }
        }
        return;
      }
      setError(message);
    } finally {
      setPending(null);
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

      {activities.length > 0 && (
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by title, subject, or activity type..."
          className="input mt-4 max-w-sm"
        />
      )}

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
      ) : filtered.length === 0 ? (
        <p className="mt-6 text-sm text-slate-500">No activities match &quot;{search}&quot;.</p>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((activity) => (
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
                  href={`/dashboard/activities/${activity.id}/preview`}
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
              <div className="mt-2 flex gap-2">
                <Link
                  href={`/dashboard/activities/${activity.id}/edit`}
                  className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-center text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  Edit
                </Link>
                <button
                  onClick={() => handleDuplicate(activity.id)}
                  disabled={pending === `${activity.id}-duplicate`}
                  className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  {pending === `${activity.id}-duplicate` ? "Duplicating..." : "Duplicate"}
                </button>
                {confirmingDelete === activity.id ? (
                  <>
                    <button
                      onClick={() => handleDelete(activity.id)}
                      disabled={pending === `${activity.id}-delete`}
                      className="flex-1 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50"
                    >
                      {pending === `${activity.id}-delete` ? "Deleting..." : "Confirm Delete"}
                    </button>
                    <button
                      onClick={() => setConfirmingDelete(null)}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => handleDelete(activity.id)}
                    className="flex-1 rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:hover:bg-red-950"
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
