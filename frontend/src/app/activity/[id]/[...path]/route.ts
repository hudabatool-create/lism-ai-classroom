/**
 * Proxies the CSS, JS and images belonging to a ZIP-uploaded activity.
 *
 * A browser resolves the entry HTML's relative references against the
 * directory of the URL that served it. Now that the HTML comes from
 * /activity/{id}/raw, "style.css" resolves to /activity/{id}/style.css --
 * so this catch-all has to sit at exactly this path, mirroring the backend
 * route it forwards to. Without it, every ZIP activity would load unstyled.
 */
import { NextRequest } from "next/server";

// This code runs on LISM's own server, so it always calls the backend's real
// address -- never the "/backend" relay the browser may be using, which only
// exists in the browser and would point this fetch back at ourselves.
const API =
  process.env.BACKEND_ORIGIN ??
  (process.env.NEXT_PUBLIC_API_BASE_URL?.startsWith("http")
    ? process.env.NEXT_PUBLIC_API_BASE_URL
    : "http://localhost:8000");

export async function GET(_req: NextRequest, ctx: { params: Promise<{ id: string; path: string[] }> }) {
  const { id, path } = await ctx.params;
  const assetPath = path.map(encodeURIComponent).join("/");

  const upstream = await fetch(
    `${API}/api/activities/${encodeURIComponent(id)}/${assetPath}`,
    { cache: "no-store" }
  );

  if (!upstream.ok) {
    return new Response("Not found", { status: upstream.status });
  }

  return new Response(await upstream.arrayBuffer(), {
    status: 200,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/octet-stream",
      "Cache-Control": "no-store",
    },
  });
}
