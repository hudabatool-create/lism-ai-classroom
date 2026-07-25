"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Logo from "@/components/Logo";
import { api } from "@/lib/api";

export default function VerifyEmailPage() {
  const params = useParams<{ token: string }>();
  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");

  useEffect(() => {
    api
      .get(`/api/auth/verify-email/${params.token}`)
      .then(() => setStatus("ok"))
      .catch(() => setStatus("error"));
  }, [params.token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-6 flex justify-center">
          <Logo size="sm" />
        </div>
        {status === "checking" && <p className="text-sm text-slate-500 dark:text-slate-400">Verifying your email...</p>}
        {status === "ok" && (
          <>
            <h1 className="mb-1 text-2xl font-semibold text-slate-900 dark:text-white">Email verified</h1>
            <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">Your email address is now confirmed.</p>
          </>
        )}
        {status === "error" && (
          <>
            <h1 className="mb-1 text-2xl font-semibold text-slate-900 dark:text-white">Link expired</h1>
            <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
              This verification link is invalid or has expired. You can request a new one from your dashboard.
            </p>
          </>
        )}
        <Link
          href="/dashboard"
          className="inline-block w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
