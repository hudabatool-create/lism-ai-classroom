"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    // The session cookie is httpOnly, so the frontend can't just check for it
    // locally -- it has to ask the backend whether the cookie it's holding
    // is actually valid.
    api
      .get("/api/auth/me")
      .then(() => {
        if (!cancelled) setReady(true);
      })
      .catch(() => {
        if (!cancelled) router.replace("/login");
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!ready) {
    return <div className="flex h-screen items-center justify-center text-slate-400">Loading...</div>;
  }

  return <>{children}</>;
}
