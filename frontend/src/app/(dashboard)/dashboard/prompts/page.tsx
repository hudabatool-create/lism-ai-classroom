"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Prompt } from "@/lib/types";

const ACTIVITY_TYPES = [
  "Interactive Lesson Deck",
  "Interactive Worksheet",
  "Quiz",
  "Multiple Choice",
  "Poll",
  "Exit Ticket",
  "Flashcards",
  "Matching",
];

const HANDOFF_KEY = "lism_prompt_handoff";

export default function PromptLibraryPage() {
  const router = useRouter();
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", category: "", activity_type: ACTIVITY_TYPES[0], body: "" });
  const [saving, setSaving] = useState(false);

  function load() {
    api
      .get<Prompt[]>("/api/prompts")
      .then(setPrompts)
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post<Prompt>("/api/prompts", form);
      setForm({ title: "", category: "", activity_type: ACTIVITY_TYPES[0], body: "" });
      setShowForm(false);
      load();
    } finally {
      setSaving(false);
    }
  }

  async function handleFavorite(id: string) {
    await api.post(`/api/prompts/${id}/favorite`);
    load();
  }

  async function handleDelete(id: string) {
    setPrompts((prev) => prev.filter((p) => p.id !== id));
    await api.delete(`/api/prompts/${id}`);
  }

  function handleUseInGenerator(prompt: Prompt) {
    sessionStorage.setItem(HANDOFF_KEY, JSON.stringify({ activity_type: prompt.activity_type, body: prompt.body }));
    router.push("/dashboard/activities/new");
  }

  const visible = showFavoritesOnly ? prompts.filter((p) => p.is_favorite) : prompts;

  return (
    <div className="max-w-3xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Prompt Library</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Only prompts that generate LISM-compatible activities live here. Save your own, favorite the ones you
            reuse, and load any of them straight into the generator.
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
        >
          {showForm ? "Cancel" : "New Prompt"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mt-4 space-y-3 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
        >
          <input
            required
            placeholder="Title"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            className="input"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Category (e.g. Math, Grade 7)"
              value={form.category}
              onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
              className="input"
            />
            <select
              value={form.activity_type}
              onChange={(e) => setForm((f) => ({ ...f, activity_type: e.target.value }))}
              className="input"
            >
              {ACTIVITY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <textarea
            required
            placeholder="Paste your master prompt or reusable prompt text..."
            value={form.body}
            onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
            className="input"
            rows={6}
          />
          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Prompt"}
          </button>
        </form>
      )}

      <div className="mt-6 flex gap-2">
        <button
          onClick={() => setShowFavoritesOnly(false)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
            !showFavoritesOnly ? "bg-brand-600 text-white" : "border border-slate-300 dark:border-slate-700"
          }`}
        >
          All
        </button>
        <button
          onClick={() => setShowFavoritesOnly(true)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
            showFavoritesOnly ? "bg-brand-600 text-white" : "border border-slate-300 dark:border-slate-700"
          }`}
        >
          Favorites
        </button>
      </div>

      {loading ? (
        <p className="mt-6 text-sm text-slate-500">Loading...</p>
      ) : (
        <div className="mt-4 space-y-3">
          {visible.map((prompt) => (
            <div
              key={prompt.id}
              className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-slate-900 dark:text-white">{prompt.title}</h3>
                    {prompt.is_builtin && (
                      <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-slate-800 dark:text-brand-300">
                        Official
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {prompt.category || "Uncategorized"} &middot; {prompt.activity_type}
                  </p>
                </div>
                {!prompt.is_builtin && (
                  <button
                    onClick={() => handleFavorite(prompt.id)}
                    className={`text-lg ${prompt.is_favorite ? "text-amber-400" : "text-slate-300 dark:text-slate-600"}`}
                    aria-label="Toggle favorite"
                  >
                    ★
                  </button>
                )}
              </div>

              <button
                onClick={() => setExpanded(expanded === prompt.id ? null : prompt.id)}
                className="mt-2 text-xs font-medium text-brand-600 hover:underline"
              >
                {expanded === prompt.id ? "Hide prompt text" : "Preview prompt text"}
              </button>
              {expanded === prompt.id && (
                <pre className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {prompt.body}
                </pre>
              )}

              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => handleUseInGenerator(prompt)}
                  className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
                >
                  Use in Generator
                </button>
                {!prompt.is_builtin && (
                  <button
                    onClick={() => handleDelete(prompt.id)}
                    className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:hover:bg-red-950"
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
