/**
 * LISM is one site to a student, but it was two addresses to a school web
 * filter: the pages come from lismlesson.com and every piece of data came
 * from the backend's own address on Railway. Both had to be allowed, and on
 * school devices where only one was, students saw a page that loaded and then
 * said "Failed to fetch" -- photographed on a school tablet, 23 Sept 2026.
 *
 * This rewrite lets the browser fetch everything from lismlesson.com itself
 * and relays it to the backend server-side, where no filter is in the way. It
 * only takes effect when NEXT_PUBLIC_API_BASE_URL is set to "/backend"; leave
 * that pointing at the backend's own address and nothing changes, which is
 * also how to undo this in one setting if it ever misbehaves.
 *
 * WebSockets cannot travel through a rewrite, so they keep going direct --
 * see lib/api.ts. Losing the socket costs responsiveness, not correctness:
 * the student page polls as well, by design.
 */
const BACKEND_ORIGIN =
  process.env.BACKEND_ORIGIN ??
  // Falls back to the old single-address setup, so a deployment that has not
  // been told about BACKEND_ORIGIN yet keeps working exactly as before.
  (process.env.NEXT_PUBLIC_API_BASE_URL?.startsWith("http")
    ? process.env.NEXT_PUBLIC_API_BASE_URL
    : "http://localhost:8000");

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [{ source: "/backend/:path*", destination: `${BACKEND_ORIGIN}/:path*` }];
  },
};

module.exports = nextConfig;
