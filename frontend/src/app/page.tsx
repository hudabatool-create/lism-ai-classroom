import Link from "next/link";
import Logo from "@/components/Logo";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 text-center dark:bg-slate-950">
      <Logo size="lg" />
      <p className="mt-4 text-sm font-semibold uppercase tracking-wide text-brand-600">LISM AI Classroom</p>
      <h1 className="mt-2 max-w-2xl text-4xl font-bold text-slate-900 dark:text-white">
        Create. Engage. Monitor. Analyze. Inspire.
      </h1>
      <p className="mt-4 max-w-xl text-slate-500 dark:text-slate-400">
        Launch interactive classroom activities, watch student responses live, and get AI-powered teaching
        insights &mdash; all in one place.
      </p>
      <div className="mt-8 flex gap-3">
        <Link
          href="/login"
          className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Log in
        </Link>
        <Link
          href="/signup"
          className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Sign up
        </Link>
      </div>
    </main>
  );
}
