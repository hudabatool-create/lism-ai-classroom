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

      {/* A web filter's classifier reads this page and follows its links. With
          nothing here but a join box, the site was filed under a generic
          category and blocked on the school's student devices. These lines say
          plainly what this is and lead to the pages that explain it. */}
      <footer className="mt-16 max-w-xl">
        <p className="text-xs leading-6 text-slate-500 dark:text-slate-400">
          LISM Lesson is an educational platform used by teachers at Liwa International School Al
          Mushrif, Abu Dhabi, UAE, to run lessons in class. It carries no advertising and no public
          content, and a lesson can only be opened with a code given by a teacher.
        </p>
        <nav className="mt-4 flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs text-slate-500 dark:text-slate-400">
          <Link href="/about" className="hover:underline">About</Link>
          <Link href="/privacy" className="hover:underline">Privacy</Link>
          <Link href="/terms" className="hover:underline">Terms</Link>
          <Link href="/contact" className="hover:underline">Contact</Link>
        </nav>
      </footer>
    </main>
  );
}
