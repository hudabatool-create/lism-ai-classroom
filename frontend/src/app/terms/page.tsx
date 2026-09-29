import type { Metadata } from "next";
import Link from "next/link";
import PublicPage from "@/components/PublicPage";

export const metadata: Metadata = {
  title: "Terms of use — LISM Lesson",
  description:
    "Terms of use for LISM Lesson, an educational platform used by teachers at Liwa International School Al Mushrif.",
};

export default function TermsPage() {
  return (
    <PublicPage title="Terms of use">
      <p className="text-sm text-slate-500 dark:text-slate-400">Last updated: September 2026</p>

      <p>
        LISM Lesson is provided for use by teachers and students of Liwa International School Al Mushrif,
        during lessons. It is offered free of charge and is not a commercial service.
      </p>

      <h2>Teacher accounts</h2>
      <ul>
        <li>Accounts are for teaching staff. A teacher is responsible for keeping their password private.</li>
        <li>A teacher sees only their own activities, sessions and students.</li>
      </ul>

      <h2>Students</h2>
      <ul>
        <li>Students do not create accounts and do not set passwords.</li>
        <li>A student joins a lesson with a code given by their teacher, and sees only their own work.</li>
      </ul>

      <h2>Acceptable use</h2>
      <ul>
        <li>The platform is for classroom teaching and learning.</li>
        <li>It carries no public content, no messaging between students and no file sharing.</li>
        <li>The school&apos;s own acceptable-use and digital policies apply in full.</li>
      </ul>

      <h2>Availability</h2>
      <p>
        The platform is maintained by one teacher alongside their teaching. It is offered as it is, with
        no guarantee of availability, and a teacher should always be able to run their lesson without it.
      </p>

      <h2>Student information</h2>
      <p>
        What is stored, where, and for how long is set out in the{" "}
        <Link href="/privacy">privacy notice</Link>.
      </p>
    </PublicPage>
  );
}
