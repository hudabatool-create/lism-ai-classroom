/**
 * Holds every student's screen on the stage the teacher started.
 *
 * Asking an activity to behave is not control. LISM sends start_stage and
 * hopes the activity hides its other sections -- but a deck written before
 * LISM existed, or one whose author's AI ignored the instruction, keeps its
 * Next button and lets a student read and answer the whole lesson while the
 * teacher is still on the starter.
 *
 * Now that the activity is served from LISM's own origin, we can stop asking.
 * This runs inside the activity's document and enforces three things:
 *
 *   1. the section for the current stage is the only one visible
 *   2. the activity's own navigation is gone -- buttons, keys, swipes
 *   3. it stays that way, re-asserted whenever the page tries to change
 *
 * Point 3 is what actually makes it hold. We do not need to find every way a
 * given activity might move itself; we only need to notice and undo it.
 *
 * Deliberately conservative: if no recognisable sections are found, it does
 * nothing at all rather than risk blanking an activity it does not understand.
 */

/** Words on a control that exists to move between sections. */
const NAV_TEXT = /^(next|prev|previous|back|continue|skip|forward|→|←|»|«)\b/i;

const NAV_SELECTORS = [
  "[data-nav]", "[data-next]", "[data-prev]",
  ".next", ".prev", ".previous", ".nav-next", ".nav-prev",
  ".slide-nav", ".navigation", ".dots", ".progress-dots", ".slide-counter",
].join(",");

const SECTION_SELECTORS = "[data-stage]";

export interface LockstepHandle {
  /** Show only this stage. Pass null to hide everything. */
  showStage: (stageId: string | null, index: number) => void;
  destroy: () => void;
}

/**
 * @param doc   the activity's document (same-origin, or this cannot work)
 * @returns a handle, or null when the activity has no sections we recognise
 */
export function installLockstep(doc: Document): LockstepHandle | null {
  const explicit = Array.from(doc.querySelectorAll<HTMLElement>(SECTION_SELECTORS));

  // Fall back to top-level sections for activities that never declared stages
  // -- the same guess stage-recovery makes on the server.
  const sections = explicit.length
    ? explicit
    : Array.from(doc.body?.querySelectorAll<HTMLElement>(":scope > section") ?? []);

  if (sections.length < 2) return null;

  let currentIndex = -1;

  const stageIdOf = (el: HTMLElement) => el.dataset.stage ?? el.id ?? "";

  function apply() {
    sections.forEach((el, i) => {
      const shouldShow = i === currentIndex;
      // setProperty with "important" so an activity's own stylesheet or
      // inline style cannot win the fight and reveal a later slide.
      if (shouldShow) {
        el.style.removeProperty("display");
        el.removeAttribute("aria-hidden");
      } else {
        el.style.setProperty("display", "none", "important");
        el.setAttribute("aria-hidden", "true");
      }
    });
    stripNav();
  }

  function stripNav() {
    const candidates = new Set<HTMLElement>();
    doc.querySelectorAll<HTMLElement>(NAV_SELECTORS).forEach((el) => candidates.add(el));
    doc.querySelectorAll<HTMLElement>("button, a, [role='button']").forEach((el) => {
      const label = (el.textContent ?? "").trim();
      // Short label only: "Next" is navigation, "Next, explain your answer"
      // is almost certainly instructional text, not a control.
      if (label.length <= 14 && NAV_TEXT.test(label)) candidates.add(el);
    });
    candidates.forEach((el) => {
      el.style.setProperty("display", "none", "important");
      el.setAttribute("data-lism-hidden", "1");
    });
  }

  // Arrow keys, page keys and space are how most decks advance. Swallow them
  // before the activity's own handler sees them -- unless the student is
  // typing, where space and arrows are ordinary editing keys.
  const keyGuard = (e: KeyboardEvent) => {
    const el = e.target as HTMLElement | null;
    const typing = !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
    if (typing) return;
    if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "PageUp", "PageDown", " ", "Home", "End"].includes(e.key)) {
      e.stopImmediatePropagation();
      e.preventDefault();
    }
  };
  doc.addEventListener("keydown", keyGuard, true);

  const touchGuard = (e: TouchEvent) => {
    const el = e.target as HTMLElement | null;
    if (el && el.closest("input, textarea, [contenteditable]")) return;
    if (e.touches.length > 1) e.preventDefault();      // pinch-swipe carousels
  };
  doc.addEventListener("touchmove", touchGuard, { passive: false, capture: true });

  // The watchdog. Whatever the activity does to change slides, this puts it
  // back -- which means we never have to enumerate the ways it might try.
  const observer = new MutationObserver(() => apply());
  observer.observe(doc.body, {
    attributes: true, attributeFilter: ["style", "class", "hidden"],
    childList: true, subtree: true,
  });

  return {
    showStage(stageId, index) {
      // Match on the declared id first; fall back to position, so an activity
      // whose ids do not match the manifest still moves in step.
      const byId = stageId ? sections.findIndex((el) => stageIdOf(el) === stageId) : -1;
      currentIndex = byId >= 0 ? byId : Math.min(index, sections.length - 1);
      if (stageId === null) currentIndex = -1;
      apply();
    },
    destroy() {
      observer.disconnect();
      doc.removeEventListener("keydown", keyGuard, true);
      doc.removeEventListener("touchmove", touchGuard, true);
    },
  };
}
