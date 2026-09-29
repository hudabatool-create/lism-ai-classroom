import type { Metadata } from "next";
import Link from "next/link";
import Logo from "@/components/Logo";
import PublicPage from "@/components/PublicPage";

export const metadata: Metadata = {
  title: "About LISM Lesson — classroom teaching platform",
  description:
    "LISM Lesson is an educational platform used by teachers at Liwa International School Al Mushrif to run teacher-paced lessons in class. Teachers control the pace; students answer on their own screens.",
};

export default function AboutPage() {
  return (
    <PublicPage title="About LISM Lesson">
      <p>
        <strong>LISM Lesson is a classroom teaching platform.</strong> It is used by teachers at Liwa
        International School Al Mushrif in Abu Dhabi, United Arab Emirates, to deliver lessons in
        class, on school devices, during lesson time.
      </p>

      <h2>What it does</h2>
      <p>
        A teacher prepares a lesson, uploads it, and starts it for the class. Students open the site on
        a school laptop or tablet and enter a six-character code the teacher reads out. From then on the
        teacher controls the pace: students cannot move to the next section until the teacher starts it,
        and cannot skip ahead or fall behind.
      </p>
      <p>
        As students answer, their work appears on the teacher&apos;s screen. Questions with a clear right
        answer are marked immediately; written answers are left for the teacher to read and mark. At the
        end, the teacher exports the marks.
      </p>

      <h2>Who it is for</h2>
      <p>
        Teachers and their students, in school. Lessons can be written and taught in English or in
        Arabic, so it is used across subjects rather than only English-medium ones. There is no public
        content, no community area, no messaging between students, and nothing to browse: a student
        who opens the site without a lesson code from their teacher sees only a box asking for one.
      </p>

      <h2>What it is not</h2>
      <ul>
        <li>It is not a social network, a forum, or a messaging service.</li>
        <li>It does not host user-generated public content of any kind.</li>
        <li>It does not carry advertising, and it sells nothing.</li>
        <li>It is not a file-sharing or hosting service.</li>
        <li>It is not open to the public — a lesson is only reachable with a code from a teacher.</li>
      </ul>

      <h2>School and contact</h2>
      <p>
        LISM Lesson was built and is maintained by a Computer Science teacher at Liwa International
        School Al Mushrif for use in that school&apos;s own lessons.
      </p>
      <p>
        For questions about this site, including web-filtering categorisation, please see the{" "}
        <Link href="/contact">contact page</Link>. How student information is handled is described in
        the <Link href="/privacy">privacy notice</Link>.
      </p>

      <div className="mt-10 flex justify-center">
        <Logo size="sm" />
      </div>
    </PublicPage>
  );
}
