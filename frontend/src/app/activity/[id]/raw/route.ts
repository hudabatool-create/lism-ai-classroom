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
import { NextRequest } from "next/server";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;

  // Forward ?preview=1 so an activity built to the LISM contract knows it is
  // being reviewed by a teacher and emits no student events.
  const preview = req.nextUrl.searchParams.get("preview") === "1" ? "?preview=1" : "";

  const upstream = await fetch(`${API}/api/activities/${encodeURIComponent(id)}/raw${preview}`, {
    // Activities change when a teacher edits or re-uploads, and a stale copy
    // would be invisible and baffling. They are small, so never cache.
    cache: "no-store",
  });

  if (!upstream.ok) {
    return new Response("Activity not found", { status: upstream.status });
  }

  return new Response(await upstream.text(), {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
