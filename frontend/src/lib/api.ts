// The backend's own address, as configured for this deployment.
const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// What the browser actually calls.
//
// A school web filter sees LISM's pages and LISM's data as two unrelated
// sites, because they come from two different addresses. Devices allowed one
// but not the other showed a lesson that loaded and then said "Failed to
// fetch" -- photographed on a school tablet, 23 Sept 2026. So in the browser
// every request goes to a path on LISM's own origin, which next.config.js
// relays to the backend server-side, where no filter is in the way.
//
// On the server there is nothing to relay through and no filter to avoid, so
// server code keeps calling the backend directly. Local development does too:
// there both addresses are the same machine, and going direct keeps the
// network traffic honest about where it is really going.
const RELAY_PATH = "/backend";
const isBrowser = typeof window !== "undefined";
const isSeparateAddress =
  isBrowser &&
  /^https?:\/\//.test(BACKEND_URL) &&
  new URL(BACKEND_URL).origin !== window.location.origin;
const API_BASE_URL = isSeparateAddress ? RELAY_PATH : BACKEND_URL;

// A WebSocket cannot be opened through that relay, so it always goes straight
// to the backend. On a device where that address is blocked the socket simply
// never opens, and the page falls back to polling -- which is what correctness
// rides on anyway. See the long note in join/[code]/page.tsx.
const WS_BASE_URL = BACKEND_URL.replace(/^http/, "ws");

// Auth lives in an httpOnly cookie the backend sets on login/signup --
// there's no token in JS to store or attach, `credentials: "include"` is what
// makes the browser send it. See AuthGuard, which asks the backend directly
// (GET /api/auth/me) instead of checking local state for a token.

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  // Never serve an API response from the browser cache.
  //
  // Nothing here sent cache headers, so browsers applied their own heuristics
  // and happily replayed an old response. On the student page that was fatal:
  // it polls the live session state, and a cached copy meant it was told
  // "no stage running" for the entire lesson, however many times it asked.
  // Only rejoining worked, because that is a POST and POSTs are never cached.
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response had no JSON body
    }
    throw new Error(detail);
  }

  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return undefined as T;
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}${path}`, { credentials: "include" });
  if (!res.ok) throw new Error("Download failed");

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  base: API_BASE_URL,
  wsBase: WS_BASE_URL,
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  postForm: <T,>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
  patch: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: <T,>(path: string) => request<T>(path, { method: "DELETE" }),
};
