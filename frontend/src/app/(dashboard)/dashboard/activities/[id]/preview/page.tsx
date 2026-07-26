"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Activity } from "@/lib/types";

/**
 * Teacher preview: walk the whole activity before launching it.
 *
 * Previously "Preview" opened the raw HTML directly, which shows only the
 * first section -- the activity waits for LISM to tell it which stage to
 * show, and standalone there is nobody to tell it. This page is that
 * missing driver: it hosts the activity and sends the same start_stage
 * commands the live student page sends, so Previous/Next step through every
 * stage exactly as students will see them.
 *
 * It creates no student data: no session, no participant, no responses. The
 * iframe is loaded with ?preview=1 so an activity built to the LISM contract
 * also suppresses its own event emission.
 */
export default function ActivityPreviewPage() {
  const params = useParams<{ id: string }>();
  const activityId = params.id;
  const [activity, setActivity] = useState<Activity | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<Activity>(`/api/activities/${activityId}`)
      .then((a) => {
        if (!cancelled) setActivity(a);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load this activity");
      });
    return () => {
      cancelled = true;
    };
  }, [activityId]);

  const stages = activity?.manifest?.stages ?? [];
  const total = stages.length;

  const showStage = useCallback(
    (i: number) => {
      const stage = stages[i];
      if (!stage) return;
      iframeRef.current?.contentWindow?.postMessage(
        { type: "lism:command", command: "start_stage", stage, stageIndex: i },
        "*"
      );
    },
    [stages]
  );

  // Re-send on every move and once the iframe is ready. Cheap, and it keeps
  // the activity in step even if it loaded after the first command was sent.
  useEffect(() => {
    if (total > 0) showStage(index);
  }, [index, total, showStage]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight") setIndex((i) => Math.min(i + 1, total - 1));
      if (e.key === "ArrowLeft") setIndex((i) => Math.max(i - 1, 0));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [total]);

  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950">
        <p className="text-sm font-semibold text-red-700 dark:text-red-400">Could not load this activity</p>
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }
  if (!activity) return <p className="text-sm text-slate-500">Loading preview...</p>;

  const current = stages[index];
  const progress = total > 0 ? ((index + 1) / total) * 100 : 0;
  const unmanaged = activity.manifest?.managed === false;

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-600">
            Preview &mdash; not a live lesson, nothing is recorded
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{activity.title}</h1>
        </div>
        <Link
          href="/dashboard/activities"
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
        >
          Back to My Activities
        </Link>
      </div>

      {unmanaged && (
        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
          This activity has no LISM manifest, so it runs as a single section. Previous and Next have nothing to step
          through &mdash; it will still launch and work, but the class can&apos;t be paced through it stage by stage.
        </p>
      )}

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-900 dark:text-white">
              {current ? current.label : "No sections"}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Section {total === 0 ? 0 : index + 1} of {total}
              {current?.durationSeconds ? ` · recommended ${Math.round(current.durationSeconds / 60)} min` : ""}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIndex((i) => Math.max(i - 1, 0))}
              disabled={index === 0}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              &larr; Previous
            </button>
            <button
              onClick={() => setIndex((i) => Math.min(i + 1, total - 1))}
              disabled={index >= total - 1}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40"
            >
              Next &rarr;
            </button>
          </div>
        </div>

        <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
          <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${progress}%` }} />
        </div>

        <ol className="mt-3 flex flex-wrap gap-2">
          {stages.map((stage, i) => (
            <li key={stage.id}>
              <button
                onClick={() => setIndex(i)}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
                  i === index
                    ? "border-brand-500 bg-brand-50 text-brand-700 dark:bg-slate-800 dark:text-brand-300"
                    : "border-slate-200 text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
                }`}
              >
                {i + 1}. {stage.label}
              </button>
            </li>
          ))}
        </ol>
      </div>

      <iframe
        ref={iframeRef}
        onLoad={() => showStage(index)}
        src={`${api.base}/api/activities/${activityId}/raw?preview=1`}
        title={`Preview of ${activity.title}`}
        className="mt-4 min-h-0 flex-1 w-full rounded-2xl border border-slate-200 bg-white dark:border-slate-800"
      />
    </div>
  );
}
