/**
 * Actually stops copying and pasting, rather than asking the activity to.
 *
 * "Copy & paste protection" was only ever a set_config message posted into the
 * activity, which every activity is free to ignore -- and one generated
 * outside LISM has never heard of it. A teacher switched the setting on before
 * an assessment, saw it switch on, and students went on pasting answers. A
 * protection that silently does nothing is worse than none at all: it is
 * believed.
 *
 * The activity is served from LISM's own origin, so the events can be stopped
 * where they happen. Applied to the student's page and, when reachable, to the
 * activity's document too.
 *
 * Scope is deliberate. It blocks copying out of and pasting into the work; it
 * does not try to defeat a determined student with a second device or a phone
 * camera, and nothing here should be described to teachers as if it does.
 */

const BLOCKED_EVENTS = ["copy", "cut", "paste", "dragstart", "drop", "contextmenu"] as const;

/** Ctrl/Cmd shortcuts that copy, cut, paste or select everything. */
const BLOCKED_KEYS = new Set(["c", "x", "v", "a", "insert"]);

export interface CopyGuardOptions {
  /** Called when a student is stopped, so the page can explain why. */
  onBlocked?: (action: string) => void;
}

/**
 * @returns a function that removes every listener again, so protection can be
 *          switched back off mid-lesson without reloading anyone's screen.
 */
export function installCopyGuard(doc: Document, options: CopyGuardOptions = {}): () => void {
  const stop = (event: Event) => {
    event.preventDefault();
    event.stopPropagation();
    options.onBlocked?.(event.type);
  };

  const keyGuard = (event: KeyboardEvent) => {
    if (!(event.ctrlKey || event.metaKey)) return;
    if (!BLOCKED_KEYS.has(event.key.toLowerCase())) return;
    // Select-all is only worth blocking inside the work itself; blocking it
    // everywhere would stop a student selecting text in their own answer box
    // to correct it.
    const el = event.target as HTMLElement | null;
    const typing =
      !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
    if (event.key.toLowerCase() === "a" && !typing) return;
    event.preventDefault();
    event.stopPropagation();
    options.onBlocked?.("shortcut");
  };

  BLOCKED_EVENTS.forEach((name) => doc.addEventListener(name, stop, true));
  doc.addEventListener("keydown", keyGuard, true);

  // Belt and braces: some browsers will still offer a selection menu on a long
  // press even with copy blocked. Removing the selection removes the offer.
  const style = doc.createElement("style");
  style.setAttribute("data-lism-copy-guard", "1");
  style.textContent = `
    [data-lism-noselect], [data-lism-noselect] * {
      -webkit-user-select: none !important;
      user-select: none !important;
      -webkit-touch-callout: none !important;
    }
    /* Answer boxes stay selectable -- a student must be able to edit what
       they typed. It is copying out and pasting in that is blocked. */
    input, textarea, [contenteditable="true"] {
      -webkit-user-select: text !important;
      user-select: text !important;
    }
  `;
  doc.head?.appendChild(style);
  doc.body?.setAttribute("data-lism-noselect", "1");

  return () => {
    BLOCKED_EVENTS.forEach((name) => doc.removeEventListener(name, stop, true));
    doc.removeEventListener("keydown", keyGuard, true);
    style.remove();
    doc.body?.removeAttribute("data-lism-noselect");
  };
}
