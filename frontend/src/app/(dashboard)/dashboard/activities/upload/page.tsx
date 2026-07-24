"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { api } from "@/lib/api";
import type { Activity } from "@/lib/types";

export default function UploadActivityPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [grade, setGrade] = useState("");
  const [activityType, setActivityType] = useState("Custom Upload");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<Activity | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Choose an .html file to upload");
      return;
    }
    setLoading(true);
    setError(null);
    const form = new FormData();
    form.append("title", title);
    form.append("subject", subject);
    form.append("grade", grade);
    form.append("activity_type", activityType);
    form.append("file", file);
    try {
      const activity = await api.postForm<Activity>("/api/activities/upload", form);
      setCreated(activity);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Upload HTML Activity</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Upload an activity built with ChatGPT, Claude, Gemini, Copilot, or hand-coded HTML. LISM hosts it for you
        &mdash; no deployment needed.
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
      >
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Title</span>
          <input required value={title} onChange={(e) => setTitle(e.target.value)} className="input" />
        </label>
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Subject</span>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} className="input" />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Grade</span>
            <input value={grade} onChange={(e) => setGrade(e.target.value)} className="input" />
          </label>
        </div>
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Activity Type</span>
          <input value={activityType} onChange={(e) => setActivityType(e.target.value)} className="input" />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">HTML File</span>
          <input
            type="file"
            accept=".html,.htm"
            required
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-brand-600 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-brand-700 dark:text-slate-300"
          />
        </label>

        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {loading ? "Uploading..." : "Upload Activity"}
        </button>
      </form>

      {created && (
        <div className="mt-6 rounded-2xl border border-green-200 bg-green-50 p-5 dark:border-green-900 dark:bg-green-950">
          <p className="font-semibold text-green-800 dark:text-green-300">
            &quot;{created.title}&quot; uploaded and hosted.
          </p>
          <div className="mt-3 flex gap-3">
            <a
              href={`${api.base}/api/activities/${created.id}/raw`}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-green-300 px-3 py-2 text-sm font-medium text-green-800 hover:bg-green-100 dark:border-green-800 dark:text-green-300"
            >
              Preview
            </a>
            <button
              onClick={() => router.push("/dashboard/activities")}
              className="rounded-lg bg-green-700 px-3 py-2 text-sm font-medium text-white hover:bg-green-800"
            >
              Go to My Activities
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
