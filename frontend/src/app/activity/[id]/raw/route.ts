/**
 * Serves an uploaded activity from LISM's own origin.
 *
 * The obvious thing is to point the iframe straight at the backend, and that
 * is what LISM used to do. But then the iframe is cross-origin and the page
 * around it can only *ask* the activity to behave -- it cannot reach in and
 * enforce anything. An activity that ignores start_stage, or that a teacher
 * wrote before LISM existed, lets students click through the whole lesson.
 *
 * Proxying the HTML through here makes the iframe same-origin, which is what
 * lets the student page hold every screen on the stage the teacher started.
 * See lib/lockstep.ts for what is then enforced.
 */
import { createHash } from "crypto";
import { NextRequest } from "next/server";

// This code runs on LISM's own server, so it always calls the backend's real
// address -- never the "/backend" relay the browser may be using, which only
// exists in the browser and would point this fetch back at ourselves.
const API =
  process.env.BACKEND_ORIGIN ??
  (process.env.NEXT_PUBLIC_API_BASE_URL?.startsWith("http")
    ? process.env.NEXT_PUBLIC_API_BASE_URL
    : "http://localhost:8000");

export async function GET(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;

  // Forward ?preview=1 so an activity built to the LISM contract knows it is
  // being reviewed by a teacher and emits no student events.
  const isPreview = req.nextUrl.searchParams.get("preview") === "1";

  // The student page passes ?v=<the activity's updated_at>. A deck that has
  // not been re-uploaded therefore keeps the same URL, and a deck that has
  // gets a brand new one -- so a versioned request can be cached as hard as
  // we like and still never serve yesterday's slides.
  const version = req.nextUrl.searchParams.get("v");

  const upstream = await fetch(
    `${API}/api/activities/${encodeURIComponent(id)}/raw${isPreview ? "?preview=1" : ""}`,
    {
      // Activities change when a teacher edits or re-uploads, and a stale copy
      // would be invisible and baffling. They are small, so never cache.
      cache: "no-store",
    },
  );

  if (!upstream.ok) {
    return new Response("Activity not found", { status: upstream.status });
  }

  const html = await upstream.text();

  // A teacher previewing is editing: never hand them anything but the file as
  // it is on the server this second.
  if (isPreview) {
    return new Response(html, {
      status: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  }

  // A fingerprint of the file itself, so a device that already has this exact
  // deck is told "unchanged" in a few hundred bytes instead of downloading
  // the whole thing again. Correctness does not depend on it: the tag changes
  // the moment a single character of the activity does.
  const etag = `"${createHash("sha1").update(html).digest("base64url")}"`;

  const cacheControl = version
    ? // Safe to hold for a long time, on the device and at the edge nearest the
      // school, precisely because re-uploading changes the URL. This is what
      // stops 28 devices each pulling the deck across the world every lesson.
      "public, max-age=3600, s-maxage=31536000, stale-while-revalidate=86400, immutable"
    : // No version to go on (an older link, or the teacher's own preview pane),
      // so check with us every time -- but a 304 still saves the download.
      "no-cache";

  const headers = {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": cacheControl,
    ETag: etag,
  };

  const seen = req.headers.get("if-none-match");
  // A revalidating browser may send several tags, and a proxy may weaken one.
  if (seen && seen.split(",").some((t) => t.trim().replace(/^W\//, "") === etag)) {
    return new Response(null, { status: 304, headers });
  }

  return new Response(html, { status: 200, headers });
}
