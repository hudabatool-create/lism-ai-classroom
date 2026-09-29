import type { MetadataRoute } from "next";

const BASE = "https://www.lismlesson.com";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: `${BASE}/`, lastModified: now, priority: 1 },
    { url: `${BASE}/about`, lastModified: now, priority: 0.8 },
    { url: `${BASE}/privacy`, lastModified: now, priority: 0.6 },
    { url: `${BASE}/terms`, lastModified: now, priority: 0.5 },
    { url: `${BASE}/contact`, lastModified: now, priority: 0.5 },
  ];
}
