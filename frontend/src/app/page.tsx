import Link from "next/link";
import Logo from "@/components/Logo";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 text-center dark:bg-slate-950">
      <Logo size="lg" />
      <p className="mt-4 text-sm font-semibold uppercase tracking-wide text-brand-600">LISM Lesson</p>
      <h1 className="mt-2 max-w-2xl text-4xl font-bold text-slate-900 dark:text-white">
        Create. Engage. Monitor. Analyze. Inspire.
      </h1>
      <p className="mt-4 max-w-xl text-slate-500 dark:text-slate-400">
        Launch interactive classroom activities, watch student responses live, and get AI-powered teaching
        insights &mdash; all in one place.
      </p>
      {/* Students outnumber teachers thirty to one, and they arrive here with
          a code in their hand. When "Log in" and "Sign up" were the two big
          buttons and joining was a line of small print underneath, a class
          read the page the way it was weighted and started creating teacher
          accounts. The primary action is now the one almost every visitor
          wants; signing in is for the one adult in the room. */}
      <Link
        href="/join"
        className="mt-8 rounded-lg bg-brand-600 px-8 py-3.5 text-base font-semibold text-white hover:bg-brand-700"
      >
        Join a lesson
      </Link>
      <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
        Enter the code your teacher gave you
      </p>
      <p className="mt-8 text-sm text-slate-500 dark:text-slate-400">
        Teacher?{" "}
        <Link href="/login" className="font-medium text-brand-600 hover:underline">
          Log in
        </Link>{" "}
        or{" "}
        <Link href="/signup" className="font-medium text-brand-600 hover:underline">
          create an account
        </Link>
      </p>
    </main>
  );
}
