"use client";

import { useEffect, useState } from "react";
import { api, downloadFile } from "@/lib/api";
import type { Activity, SessionInfo } from "@/lib/types";

export default function ReportsPage() {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.get<SessionInfo[]>("/api/sessions"), api.get<Activity[]>("/api/activities")])
      .then(([s, a]) => {
        setSessions(s);
        setActivities(a);
      })
      .finally(() => setLoading(false));
  }, []);

  const activityTitle = (id: string) => activities.find((a) => a.id === id)?.title ?? "Unknown activity";

  async function handleDownload(sessionId: string, code: string, format: "pdf" | "csv" | "excel") {
    setDownloading(`${sessionId}-${format}`);
    try {
      const extension = format === "excel" ? "xlsx" : format;
      await downloadFile(`/api/reports/${sessionId}/${format}`, `report-${code}.${extension}`);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Reports</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Export responses, completion data, and the Focus Report for any session.
      </p>

      {loading ? (
        <p className="mt-6 text-sm text-slate-500">Loading...</p>
      ) : sessions.length === 0 ? (
        <p className="mt-6 text-sm text-slate-500">
          Launch a session first &mdash; reports appear here once you have one.
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
                <th className="px-4 py-3 text-right">Export</th>
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
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => handleDownload(s.id, s.code, "pdf")}
                        disabled={downloading === `${s.id}-pdf`}
                        className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
                      >
                        PDF
                      </button>
                      <button
                        onClick={() => handleDownload(s.id, s.code, "csv")}
                        disabled={downloading === `${s.id}-csv`}
                        className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
                      >
                        CSV
                      </button>
                      <button
                        onClick={() => handleDownload(s.id, s.code, "excel")}
                        disabled={downloading === `${s.id}-excel`}
                        className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
                      >
                        Excel
                      </button>
                    </div>
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
