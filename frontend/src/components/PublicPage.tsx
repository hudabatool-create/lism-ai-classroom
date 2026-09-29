import Link from "next/link";
import type { ReactNode } from "react";

/**
 * The frame for the pages that are meant to be read rather than used:
 * about, privacy, terms, contact.
 *
 * These exist because a web filter's classifier had nothing to go on. The
 * site was a join box and forty-four words, so it was filed under a generic
 * category full of junk and blocked on the school's student devices. A site
 * that plainly says what it is, who runs it and what it does with children's
 * data is one a reviewer can categorise as Education in a few seconds.
 */
export default function PublicPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      <main className="mx-auto max-w-3xl px-5 py-14">
        <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-brand-600">LISM Lesson</p>
        <h1 className="mb-8 text-3xl font-bold text-slate-900 dark:text-white">{title}</h1>
        <div
          className="space-y-4 text-[15px] leading-7 text-slate-700 dark:text-slate-300
            [&_h2]:mt-9 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-slate-900 dark:[&_h2]:text-white
            [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-6
            [&_a]:text-brand-600 [&_a]:underline [&_strong]:text-slate-900 dark:[&_strong]:text-white"
        >
          {children}
        </div>
      </main>
      <footer className="border-t border-slate-200 py-8 dark:border-slate-800">
        <nav className="mx-auto flex max-w-3xl flex-wrap justify-center gap-x-6 gap-y-2 px-5 text-sm text-slate-500 dark:text-slate-400">
          <Link href="/">Home</Link>
          <Link href="/about">About</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
          <Link href="/contact">Contact</Link>
        </nav>
        <p className="mt-4 text-center text-xs text-slate-400">
          An educational platform for Liwa International School Al Mushrif, Abu Dhabi, UAE.
        </p>
      </footer>
    </div>
  );
}
