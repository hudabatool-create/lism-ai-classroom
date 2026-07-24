"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import Logo from "@/components/Logo";

export default function JoinWithCodePage() {
  const router = useRouter();
  const [code, setCode] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = code.trim();
    if (!trimmed) return;
    router.push(`/join/${encodeURIComponent(trimmed.toUpperCase())}`);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 text-center dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="mb-6 flex justify-center">
          <Logo size="sm" />
        </div>
        <h1 className="mb-1 text-xl font-semibold text-slate-900 dark:text-white">Join an activity</h1>
        <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
          Enter the activity code your teacher shared.
        </p>
        <input
          autoFocus
          required
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="e.g. 2U1OEI"
          className="input mb-6 text-center font-mono text-2xl tracking-widest uppercase"
        />
        <button
          type="submit"
          className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Join
        </button>
      </form>
    </div>
  );
}
