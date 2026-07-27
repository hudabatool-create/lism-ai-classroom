"use client";

/**
 * "Create an Activity" — the guided path from a master prompt to a live lesson.
 *
 * LISM deliberately does not generate activity HTML itself. Teachers get better
 * results from a full-strength assistant (ChatGPT, Claude, Gemini) than from a
 * server-side call, they can iterate on the output conversationally, and the
 * school pays nothing per activity. LISM's job starts at upload: it reads the
 * manifest, paces the stages, and monitors the class.
 *
 * Every prompt offered here already carries the LISM manifest contract, so
 * whatever the teacher's AI tool returns arrives here teacher-paced.
 */

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Prompt } from "@/lib/types";

const AI_TOOLS = [
  { name: "ChatGPT", href: "https://chat.openai.com" },
  { name: "Claude", href: "https://claude.ai" },
  { name: "Gemini", href: "https://gemini.google.com" },
];

// Placeholders every master prompt leaves for the teacher to fill in.
const PLACEHOLDERS = ["[SUBJECT]", "[GRADE]", "[WEEK X]", "[TOPIC NAME]"];

export default function CreateActivityPage() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Prompt[]>("/api/prompts")
      .then((data) => {
        const official = data.filter((p) => p.is_builtin);
        setPrompts(data);
        setSelectedId(official[0]?.id ?? data[0]?.id ?? null);
      })
      .finally(() => setLoading(false));
  }, []);

  // Group in the order the API returns them so the two full-lesson prompts stay
  // at the top, where a teacher planning a whole lesson looks first.
  const grouped = useMemo(() => {
    const groups: { category: string; prompts: Prompt[] }[] = [];
    for (const p of prompts) {
      const category = p.category || "Other";
      const existing = groups.find((g) => g.category === category);
      if (existing) existing.prompts.push(p);
      else groups.push({ category, prompts: [p] });
    }
    return groups;
  }, [prompts]);

  const selected = prompts.find((p) => p.id === selectedId) ?? null;

  useEffect(() => {
    setCopied(false);
    setCopyError(null);
  }, [selectedId]);

  async function handleCopy() {
    if (!selected) return;
    try {
      await navigator.clipboard.writeText(selected.body);
      setCopied(true);
      setCopyError(null);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Clipboard access is blocked on insecure origins and in some school
      // browser policies -- say so instead of silently doing nothing.
      setCopyError("Your browser blocked the copy. Select the prompt text below and copy it manually.");
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Create an Activity</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Build your activity with the AI tool you already use, then upload it here to run it live. Every prompt below is
        LISM-ready: the activity arrives with named stages, so you control the pacing and see every student&apos;s work
        as they go.
      </p>

      <Step number={1} title="Pick the activity you want">
        {loading ? (
          <p className="text-sm text-slate-500">Loading prompts...</p>
        ) : (
          <div className="space-y-4">
            {grouped.map((group) => (
              <div key={group.category}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
                  {group.category}
                </p>
                <div className="flex flex-wrap gap-2">
                  {group.prompts.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSelectedId(p.id)}
                      className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                        p.id === selectedId
                          ? "border-brand-600 bg-brand-600 text-white"
                          : "border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                      }`}
                    >
                      {p.title}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Step>

      <Step number={2} title="Copy the prompt and fill in your lesson details">
        {selected ? (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={handleCopy}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              >
                {copied ? "Copied!" : `Copy "${selected.title}" prompt`}
              </button>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                Works for every subject, including Arabic.
              </span>
            </div>
            {copyError && (
              <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                {copyError}
              </p>
            )}
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
              Replace these placeholders before you send it:
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {PLACEHOLDERS.map((ph) => (
                <code
                  key={ph}
                  className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                >
                  {ph}
                </code>
              ))}
            </div>
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium text-brand-600 hover:underline">
                View the prompt text
              </summary>
              <pre className="mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {selected.body}
              </pre>
            </details>
          </>
        ) : (
          <p className="text-sm text-slate-500">Choose an activity type above.</p>
        )}
      </Step>

      <Step number={3} title="Paste it into your AI tool">
        <div className="flex flex-wrap gap-2">
          {AI_TOOLS.map((tool) => (
            <a
              key={tool.name}
              href={tool.href}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Open {tool.name} &#8599;
            </a>
          ))}
        </div>
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
          Ask for the complete HTML file. If the reply gets cut off, say &quot;continue&quot; and join the parts. You can
          keep refining it in the same chat — ask for harder questions, a different context, or more Arabic vocabulary
          until it fits your class.
        </p>
      </Step>

      <Step number={4} title="Save the reply as an .html file">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Copy everything from <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">&lt;!DOCTYPE html&gt;</code>{" "}
          to <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">&lt;/html&gt;</code> into a text editor and
          save it as <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">my-lesson.html</code>. Open it once in
          your browser to check it looks right.
        </p>
      </Step>

      <Step number={5} title="Upload it and run your class" last>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          LISM reads the stages out of the file, so you start each section when your class is ready, set the timer, pause
          the room, and watch every answer come in live.
        </p>
        <div className="mt-3 flex flex-wrap gap-3">
          <Link
            href="/dashboard/activities/upload"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Upload HTML Activity
          </Link>
          <Link
            href="/dashboard/prompts"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Browse all prompts
          </Link>
        </div>
      </Step>
    </div>
  );
}

function Step({
  number,
  title,
  children,
  last,
}: {
  number: number;
  title: string;
  children: React.ReactNode;
  last?: boolean;
}) {
  return (
    <section className="relative mt-6 pl-12">
      <span className="absolute left-0 top-0 flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
        {number}
      </span>
      {!last && <span className="absolute left-4 top-9 h-[calc(100%-1rem)] w-px bg-slate-200 dark:bg-slate-800" />}
      <h2 className="mt-1 font-semibold text-slate-900 dark:text-white">{title}</h2>
      <div className="mt-3 pb-2">{children}</div>
    </section>
  );
}
