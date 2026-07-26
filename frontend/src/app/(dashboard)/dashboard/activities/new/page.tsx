"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Activity } from "@/lib/types";

const ACTIVITY_TYPES = [
  "Interactive Lesson Deck",
  "Interactive Worksheet",
  "Quiz",
  "Multiple Choice",
  "True/False",
  "Fill in the Blanks",
  "Matching",
  "Drag & Drop",
  "Crossword",
  "Flashcards",
  "Memory Game",
  "Escape Room",
  "Coding Challenge",
  "Simulation",
  "AI Chat Activity",
  "Reflection Activity",
  "Exit Ticket",
  "Starter Activity",
  "Poll",
  "Brainstorm Board",
];

const HANDOFF_KEY = "lism_prompt_handoff";

export default function GenerateActivityPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    subject: "",
    grade: "",
    topic: "",
    activity_type: ACTIVITY_TYPES[0],
    objectives: "",
    difficulty: "Medium",
    time_limit: 10,
  });
  const [customPrompt, setCustomPrompt] = useState("");
  const [showCustomPrompt, setShowCustomPrompt] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<Activity | null>(null);

  // If a prompt was handed off from the Prompt Library ("Use in Generator"),
  // load it once and clear it so a later visit doesn't reuse it by accident.
  useEffect(() => {
    const raw = sessionStorage.getItem(HANDOFF_KEY);
    if (!raw) return;
    sessionStorage.removeItem(HANDOFF_KEY);
    try {
      const handoff = JSON.parse(raw) as { activity_type: string; body: string };
      setForm((f) => ({ ...f, activity_type: handoff.activity_type || f.activity_type }));
      setCustomPrompt(handoff.body || "");
      setShowCustomPrompt(true);
    } catch {
      /* ignore malformed handoff data */
    }
  }, []);

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = { ...form, custom_prompt: customPrompt.trim() || undefined };
      const activity = await api.post<Activity>("/api/activities/generate", payload);
      setCreated(activity);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Generate Activity with AI</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Describe the lesson and let AI build an interactive HTML activity. Without an OpenAI key configured on the
        backend, this returns a working canned template so you can try the full flow today.
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Subject">
            <input required value={form.subject} onChange={(e) => update("subject", e.target.value)} className="input" />
          </Field>
          <Field label="Grade">
            <input required value={form.grade} onChange={(e) => update("grade", e.target.value)} className="input" />
          </Field>
        </div>
        <Field label="Topic">
          <input required value={form.topic} onChange={(e) => update("topic", e.target.value)} className="input" />
        </Field>
        <Field label="Learning Objectives">
          <textarea
            value={form.objectives}
            onChange={(e) => update("objectives", e.target.value)}
            className="input"
            rows={3}
          />
        </Field>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Activity Type">
            <select
              value={form.activity_type}
              onChange={(e) => update("activity_type", e.target.value)}
              className="input"
            >
              {ACTIVITY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Difficulty">
            <select value={form.difficulty} onChange={(e) => update("difficulty", e.target.value)} className="input">
              <option>Easy</option>
              <option>Medium</option>
              <option>Hard</option>
            </select>
          </Field>
          <Field label="Time Limit (min)">
            <input
              type="number"
              min={1}
              value={form.time_limit}
              onChange={(e) => update("time_limit", Number(e.target.value))}
              className="input"
            />
          </Field>
        </div>

        <div className="border-t border-slate-100 pt-4 dark:border-slate-800">
          <button
            type="button"
            onClick={() => setShowCustomPrompt((v) => !v)}
            className="text-sm font-medium text-brand-600 hover:underline"
          >
            {showCustomPrompt ? "Hide" : "Paste your own master prompt"}
          </button>
          {showCustomPrompt && (
            <div className="mt-2">
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Paste a master prompt (e.g. from the Prompt Library) — [TOPIC NAME], [SUBJECT], [GRADE] placeholders will be filled in automatically. Requires an OpenAI key on the backend to actually run."
                className="input"
                rows={6}
              />
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Browse saved prompts in the{" "}
                <Link href="/dashboard/prompts" className="text-brand-600 hover:underline">
                  Prompt Library
                </Link>
                .
              </p>
            </div>
          )}
        </div>

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
          {loading ? "Generating..." : "Generate Activity"}
        </button>
      </form>

      {created && (
        <div className="mt-6 rounded-2xl border border-green-200 bg-green-50 p-5 dark:border-green-900 dark:bg-green-950">
          <p className="font-semibold text-green-800 dark:text-green-300">&quot;{created.title}&quot; is ready.</p>
          <div className="mt-3 flex gap-3">
            <a
              href={`/dashboard/activities/${created.id}/preview`}
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

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">{label}</span>
      {children}
    </label>
  );
}
