import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

// What a web filter's classifier reads first. "Create. Engage. Monitor."
// says nothing about what this is, which is part of why the site was filed
// under a generic category and blocked on the school's student devices.
export const metadata: Metadata = {
  title: {
    default: "LISM Lesson — classroom teaching platform for schools",
    template: "%s",
  },
  description:
    "An educational platform used by teachers at Liwa International School Al Mushrif, Abu Dhabi, to run teacher-paced lessons in class. Students join with a code from their teacher and answer on their own screens.",
  applicationName: "LISM Lesson",
  keywords: ["education", "school", "classroom", "teaching", "lesson", "teacher", "students", "Liwa International School Al Mushrif"],
  category: "education",
  metadataBase: new URL("https://www.lismlesson.com"),
  openGraph: {
    type: "website",
    siteName: "LISM Lesson",
    title: "LISM Lesson — classroom teaching platform for schools",
    description:
      "An educational platform used by teachers at Liwa International School Al Mushrif to run lessons in class.",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
