"use client";

import { useState, type ReactNode } from "react";

/**
 * A status tile on the live dashboard.
 *
 * A count alone tells a teacher that three students need help but not *which*
 * three, which is the only part they can act on. Passing `students` makes the
 * tile expandable to name them.
 */
export default function StatCard({
  label,
  value,
  students,
  tone = "default",
}: {
  label: string;
  value: number | string;
  students?: { id: string; name: string; detail?: ReactNode }[];
  tone?: "default" | "alert" | "good";
}) {
  const [open, setOpen] = useState(false);
  const expandable = Array.isArray(students) && students.length > 0;

  const toneClasses =
    tone === "alert"
      ? "border-amber-300 dark:border-amber-800"
      : tone === "good"
        ? "border-green-300 dark:border-green-900"
        : "border-slate-200 dark:border-slate-800";

  return (
    <div className={`rounded-2xl border bg-white dark:bg-slate-900 ${toneClasses}`}>
      <button
        type="button"
        onClick={() => expandable && setOpen((o) => !o)}
        // Stays inert when there's nobody to list, so it doesn't invite a
        // click that does nothing.
        className={`w-full rounded-2xl p-5 text-center ${
          expandable ? "cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800" : "cursor-default"
        }`}
        aria-expanded={expandable ? open : undefined}
      >
        <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
        <p className="mt-1 text-3xl font-semibold text-slate-900 dark:text-white">{value}</p>
        {expandable && <p className="mt-1 text-xs text-brand-600">{open ? "Hide names" : "Show names"}</p>}
      </button>

      {expandable && open && (
        <ul className="max-h-60 space-y-1.5 overflow-y-auto border-t border-slate-200 px-4 py-3 text-left dark:border-slate-800">
          {students!.map((s) => (
            <li key={s.id} className="text-sm">
              <span className="font-medium text-slate-800 dark:text-slate-200">{s.name}</span>
              {s.detail && <span className="ml-2 text-xs text-slate-500 dark:text-slate-400">{s.detail}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
