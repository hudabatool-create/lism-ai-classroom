/**
 * One clock for the whole class: the server's.
 *
 * Every countdown is worked out from when the stage started, and both the
 * teacher's page and the students' pages were measuring that against their own
 * device clock. Phones and laptops are routinely several seconds apart, so a
 * teacher saw 4:31 while a student saw 4:24 on the same stage, and neither of
 * them could tell which was right.
 *
 * The server sends its own time with every session payload. The difference
 * between that and this device's clock is the offset; applying it makes every
 * screen agree, however badly a phone's clock is set.
 */

let offset = 0;

/**
 * Record how far this device's clock is from the server's.
 *
 * @param serverTime ISO timestamp the server produced as it built the response
 */
export function syncClock(serverTime: string | null | undefined): void {
  if (!serverTime) return;
  const server = new Date(serverTime).getTime();
  if (!Number.isFinite(server)) return;

  // The response spent time in flight, so the server's clock has moved on
  // since it was read. Without accounting for that, every sync would push the
  // countdown a little further behind on a slow connection.
  const next = server - Date.now();

  // A small correction each time rather than a jump, so the number on screen
  // never lurches while someone is reading it.
  offset = offset === 0 ? next : Math.round(offset * 0.7 + next * 0.3);
}

/** Now, as the server would tell it. */
export function serverNow(): number {
  return Date.now() + offset;
}

/** How far this device's clock is out, in seconds. Shown by ?debug=1. */
export function clockSkewSeconds(): number {
  return Math.round(offset / 1000);
}
