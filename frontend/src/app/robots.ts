import type { MetadataRoute } from "next";

/**
 * A filter's classifier, and any crawler, starts here. Without this file the
 * site looked like an application with nothing to read, which is how it ended
 * up in a generic blocked category on the school's student devices.
 *
 * The pages that describe what this is are open. Everything that belongs to a
 * teacher or a lesson is not: a live lesson is reachable only with a code
 * given out in class, and there is nothing there for a crawler to index.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/about", "/privacy", "/terms", "/contact"],
      disallow: ["/dashboard", "/join/", "/activity/", "/login", "/signup", "/reset-password", "/verify-email", "/forgot-password"],
    },
    sitemap: "https://www.lismlesson.com/sitemap.xml",
  };
}
