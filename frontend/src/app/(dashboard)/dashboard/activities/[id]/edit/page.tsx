"use client";

import { useParams, useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ActivityDetail } from "@/lib/types";

export default function EditActivityPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [assetFiles, setAssetFiles] = useState<string[]>([]);
  const [form, setForm] = useState({ title: "", subject: "", grade: "", activity_type: "", html: "" });

  useEffect(() => {
    api
      .get<ActivityDetail>(`/api/activities/${params.id}`)
      .then((a) => {
        setForm({ title: a.title, subject: a.subject, grade: a.grade, activity_type: a.activity_type, html: a.html });
        setAssetFiles(a.asset_files);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load activity"))
      .finally(() => setLoading(false));
  }, [params.id]);

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.patch(`/api/activities/${params.id}`, form);
      router.push("/dashboard/activities");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Loading...</p>;

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Edit Activity</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Editing changes the activity itself, not any past sessions already run from it.
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
      >
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Title</span>
          <input required value={form.title} onChange={(e) => update("title", e.target.value)} className="input" />
        </label>
        <div className="grid grid-cols-3 gap-4">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Subject</span>
            <input value={form.subject} onChange={(e) => update("subject", e.target.value)} className="input" />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Grade</span>
            <input value={form.grade} onChange={(e) => update("grade", e.target.value)} className="input" />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Activity Type</span>
            <input
              value={form.activity_type}
              onChange={(e) => update("activity_type", e.target.value)}
              className="input"
            />
          </label>
        </div>

        {assetFiles.length > 0 && (
          <p className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400">
            This activity also has {assetFiles.length} uploaded asset file(s) ({assetFiles.join(", ")}) that stay
            attached as-is &mdash; only the HTML below is editable here.
          </p>
        )}

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">HTML</span>
          <textarea
            required
            value={form.html}
            onChange={(e) => update("html", e.target.value)}
            className="input font-mono text-xs"
            rows={18}
            spellCheck={false}
          />
        </label>

        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
            {error}
          </p>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
          <button
            type="button"
            onClick={() => router.push("/dashboard/activities")}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
