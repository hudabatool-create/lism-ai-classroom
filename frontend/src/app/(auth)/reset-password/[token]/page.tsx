"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import Logo from "@/components/Logo";
import { api } from "@/lib/api";

export default function ResetPasswordPage() {
  const router = useRouter();
  const params = useParams<{ token: string }>();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Passwords don't match");
      return;
    }
    setLoading(true);
    try {
      await api.post("/api/auth/reset-password", { token: params.token, password });
      setDone(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
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
        <h1 className="mb-1 text-2xl font-semibold text-slate-900 dark:text-white">Choose a new password</h1>
        <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
          This link is single-use and expires an hour after it was sent.
        </p>
        {done ? (
          <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
            Password updated. Redirecting you to log in...
          </p>
        ) : (
          <form onSubmit={handleSubmit}>
            {error && (
              <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
                {error}
              </p>
            )}
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              New password
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input mb-4"
            />
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Confirm password
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input mb-6"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {loading ? "Saving..." : "Reset password"}
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
