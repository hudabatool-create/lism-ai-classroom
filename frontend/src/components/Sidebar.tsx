"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Logo from "@/components/Logo";
import { clearToken } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/activities", label: "My Activities" },
  { href: "/dashboard/activities/new", label: "Generate Activity with AI" },
  { href: "/dashboard/activities/upload", label: "Upload HTML Activity" },
  { href: "/dashboard/live", label: "Live Classroom" },
  { href: "/dashboard/reports", label: "Reports" },
  { href: "/dashboard/insights", label: "AI Insights" },
  { href: "/dashboard/library", label: "Activity Library" },
  { href: "/dashboard/settings", label: "Settings" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col justify-between border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div>
        <div className="px-6 py-6">
          <Logo size="sm" />
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">Create. Engage. Monitor. Analyze. Inspire.</p>
        </div>
        <nav className="flex flex-col gap-1 px-3">
          {NAV_ITEMS.map((item) => {
            const active = item.href === "/dashboard" ? pathname === item.href : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-brand-600 text-white"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="p-3">
        <button
          onClick={handleLogout}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
