import type { Metadata } from "next";
import PublicPage from "@/components/PublicPage";

export const metadata: Metadata = {
  title: "Contact — LISM Lesson",
  description:
    "How to contact the teacher who maintains LISM Lesson, including for web-filtering categorisation queries and data requests.",
};

export default function ContactPage() {
  return (
    <PublicPage title="Contact">
      <p>
        LISM Lesson is maintained by a Computer Science teacher at Liwa International School Al Mushrif,
        Abu Dhabi, United Arab Emirates.
      </p>

      <h2>For the school</h2>
      <p>
        Parents, colleagues and school leadership can reach the teacher who maintains this platform
        through the school office, or through the school&apos;s own staff directory at{" "}
        <a href="https://lism.ae">lism.ae</a>.
      </p>

      <h2>Data requests</h2>
      <p>
        To ask for a student&apos;s responses to be deleted, or to ask what has been stored about a
        particular student, contact the school office and the request will be actioned. See the privacy
        notice for what is held.
      </p>

      <h2>For web filtering and categorisation</h2>
      <p>
        This site is an educational platform used inside one school. It hosts no public user content, no
        advertising and no downloads, and it is not open to the public: a lesson can only be opened with
        a code given by a teacher in class.
      </p>
      <p>
        If you are reviewing this domain for classification, the correct category is{" "}
        <strong>Education</strong>. The about page describes what the platform does, and the privacy
        notice describes exactly what it stores.
      </p>
    </PublicPage>
  );
}
