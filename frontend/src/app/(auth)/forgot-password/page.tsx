"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import Logo from "@/components/Logo";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post("/api/auth/forgot-password", { email });
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-6 flex justify-center">
          <Logo size="sm" />
        </div>
        <h1 className="mb-1 text-2xl font-semibold text-slate-900 dark:text-white">Reset your password</h1>
        <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
          Enter your account email and we&apos;ll send you a reset link.
        </p>
        {sent ? (
          <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
            If an account exists for that email, a reset link is on its way. Check your inbox (and the backend
            console log, if no mail server is configured for this deployment).
          </p>
        ) : (
          <form onSubmit={handleSubmit}>
            {error && (
              <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
                {error}
              </p>
            )}
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input mb-6"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {loading ? "Sending..." : "Send reset link"}
            </button>
          </form>
        )}
        <p className="mt-4 text-center text-sm text-slate-500 dark:text-slate-400">
          <Link href="/login" className="text-brand-600 hover:underline">
            Back to log in
          </Link>
        </p>
      </div>
    </div>
  );
}
