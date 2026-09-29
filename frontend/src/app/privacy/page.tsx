import type { Metadata } from "next";
import Link from "next/link";
import PublicPage from "@/components/PublicPage";

export const metadata: Metadata = {
  title: "Privacy notice — LISM Lesson",
  description:
    "What LISM Lesson stores about a student, where it is stored, who can see it, and how long it is kept. An educational platform used at Liwa International School Al Mushrif.",
};

export default function PrivacyPage() {
  return (
    <PublicPage title="Privacy notice">
      <p className="text-sm text-slate-500 dark:text-slate-400">Last updated: September 2026</p>

      <p>
        LISM Lesson is used in class by teachers at Liwa International School Al Mushrif. This page
        describes exactly what it stores about a student, where, who can see it, and for how long. It is
        written to be read by a parent or a school leader, not only by a specialist.
      </p>

      <h2>What is stored about a student</h2>
      <ul>
        <li>The name the student types when joining a lesson, and their class and section.</li>
        <li>What they write in the answer boxes during the lesson.</li>
        <li>Their marks, and any written feedback their teacher gives them.</li>
        <li>Whether they pressed the &ldquo;I need help&rdquo; button, and how many times.</li>
        <li>
          In an assessment only: a count of how many times the activity window was left, because the
          teacher has switched that check on.
        </li>
      </ul>

      <h2>What is never collected</h2>
      <ul>
        <li>
          <strong>No student email addresses.</strong> Students do not create accounts and never set a
          password. They join with a code the teacher reads out in class.
        </li>
        <li>No photographs, dates of birth, contact details, addresses or identity numbers.</li>
        <li>No location data.</li>
        <li>
          <strong>No advertising, analytics or third-party tracking of any kind.</strong> The site loads
          no advertising networks and no analytics services.
        </li>
        <li>Nothing is imported from the school&apos;s own systems.</li>
      </ul>

      <h2>Who can see a student&apos;s work</h2>
      <p>
        Only the teacher who ran that lesson, after signing in to their own account. Teachers cannot see
        one another&apos;s classes. A student sees their own work and their own marks, and no one
        else&apos;s. There is no public page anywhere on this site that shows a student&apos;s name or
        their work.
      </p>

      <h2>Where it is stored</h2>
      <p>
        The website is served by Vercel, the application runs on Railway, and the information is held in
        a PostgreSQL database hosted by Supabase. Those services currently run in the United States.
        They can be moved to a region closer to the UAE, and will be if the school asks for it.
      </p>
      <p>Connections to the site are encrypted (HTTPS).</p>

      <h2>How long it is kept</h2>
      <p>
        At present, lesson responses are kept indefinitely so that a teacher can look back at earlier
        work. There is no automatic deletion yet. A teacher may ask for a lesson&apos;s responses to be
        deleted at any time, and a parent or the school may ask for a particular student&apos;s work to
        be removed; see <Link href="/contact">contact</Link>.
      </p>
      <p>
        Adding a routine retention limit is planned, and the school&apos;s own retention policy will be
        followed once one is set for this platform.
      </p>

      <h2>Cookies and what the browser stores</h2>
      <ul>
        <li>
          <strong>Teachers:</strong> one cookie that keeps them signed in. It carries no advertising or
          tracking purpose.
        </li>
        <li>
          <strong>Students:</strong> no login cookie. The browser remembers only which participant the
          student is in the lesson currently open, so that refreshing the page or a tablet going to sleep
          returns them to their own work instead of creating a duplicate.
        </li>
      </ul>

      <h2>Artificial intelligence</h2>
      <p>
        Teachers may write their lessons with the help of an AI assistant before uploading them. That
        happens outside this site, with the teacher&apos;s own material, and no student work is involved.
      </p>
      <p>
        An optional in-lesson assistant for students exists but is switched off unless the school enables
        it. While it is off, no student&apos;s work is sent to any AI service.
      </p>

      <h2>Who is responsible</h2>
      <p>
        LISM Lesson is built and maintained by a Computer Science teacher at Liwa International School Al
        Mushrif, for use in that school. Questions, corrections and deletion requests can be sent through
        the <Link href="/contact">contact page</Link>.
      </p>
    </PublicPage>
  );
}
