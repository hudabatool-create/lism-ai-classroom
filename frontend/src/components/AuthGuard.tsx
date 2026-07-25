"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Teacher } from "@/lib/types";

export default function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [teacher, setTeacher] = useState<Teacher | null>(null);

  useEffect(() => {
    let cancelled = false;
    // The session cookie is httpOnly, so the frontend can't just check for it
    // locally -- it has to ask the backend whether the cookie it's holding
    // is actually valid.
    api
      .get<{ teacher: Teacher }>("/api/auth/me")
      .then((res) => {
        if (!cancelled) setTeacher(res.teacher);
      })
      .catch(() => {
        if (!cancelled) router.replace("/login");
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!teacher) {
    return <div className="flex h-screen items-center justify-center text-slate-400">Loading...</div>;
  }

  return (
    <>
      {!teacher.email_verified && <UnverifiedBanner />}
      {children}
    </>
  );
}

function UnverifiedBanner() {
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);

  async function handleResend() {
    setSending(true);
    try {
      await api.post("/api/auth/resend-verification");
      setSent(true);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex items-center justify-between gap-4 border-b border-amber-200 bg-amber-50 px-6 py-2 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300">
      <span>Please verify your email address to secure your account.</span>
      {sent ? (
        <span className="shrink-0 font-medium">Verification email sent</span>
      ) : (
        <button onClick={handleResend} disabled={sending} className="shrink-0 font-medium hover:underline disabled:opacity-50">
          {sending ? "Sending..." : "Resend email"}
        </button>
      )}
    </div>
  );
}
