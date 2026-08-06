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
  // Worksheets print a contents strip -- "1. Header  2. Objectives  3. Starter"
  // -- along the top. It is navigation like any other: it names every section
  // the teacher has not started yet and invites a student to go there.
  ".jump-menu", ".jump-chip", ".jump-nav", ".section-nav", ".toc", ".table-of-contents",
].join(",");

/**
 * How to find an activity's slides, best evidence first.
 *
 * The first version only looked for [data-stage] or a direct <section> child
 * of <body>, and found nothing in a real deck -- whose slides were divs inside
 * a wrapper. Finding no slides meant enforcing nothing, silently, which is the
 * worst possible failure: it looks like the feature simply does not work.
 */
const SECTION_STRATEGIES = [
  "[data-stage]",
  "[data-slide]",
  ".slide:not(.slide-nav):not(.slide-counter)",
  "section.slide, div.slide, article.slide",
  "[id^='slide']",
  "[id^='section-']",
  "[id^='stage-']",
  "section",
  ".step, .panel, .screen, .page",
];

/**
 * Slides are siblings. Grouping candidates by parent and taking the biggest
 * group avoids picking up a stray <section> in a footer, or nested elements
 * that happen to match, which would hide half the real slide.
 */
function findSlides(doc: Document): HTMLElement[] {
  for (const selector of SECTION_STRATEGIES) {
    let matches: HTMLElement[];
    try {
      matches = Array.from(doc.querySelectorAll<HTMLElement>(selector));
    } catch {
      continue; // selector unsupported in this browser
    }
    if (matches.length < 2) continue;

    const byParent = new Map<Element, HTMLElement[]>();
    for (const el of matches) {
      const parent = el.parentElement;
      if (!parent) continue;
      const group = byParent.get(parent) ?? [];
      group.push(el);
      byParent.set(parent, group);
    }

    let best: HTMLElement[] = [];
    for (const group of byParent.values()) {
      if (group.length > best.length) best = group;
    }
    // Two siblings could be a header and a footer; three of a kind is a deck.
    // [data-stage] is explicit enough to trust at two.
    const enough = selector.startsWith("[data-") ? 2 : 3;
    if (best.length >= enough) return best;
  }
  return [];
}

/** What the watchdog listens for -- the ways a deck changes which slide shows. */
const OBSERVE_OPTIONS: MutationObserverInit = {
  attributes: true,
  attributeFilter: ["style", "class", "hidden"],
  childList: true,
  subtree: true,
};

/** Long enough to coalesce a burst of mutations, short enough to feel instant. */
const WATCHDOG_DELAY_MS = 50;

export interface LockstepHandle {
  /**
   * Show only this stage. Pass null to hide everything.
   *
   * @param stageId the stage's anchor or id, matched against the section's
   *                own data-stage/id
   * @param index   position in the stage list -- the last resort
   * @param label   the stage's heading as the teacher sees it, matched against
   *                the section headings when the id does not exist in the
   *                document (which is every activity whose stages were
   *                recovered before anchors were recorded)
   */
  showStage: (stageId: string | null, index: number, label?: string) => void;
  destroy: () => void;
}

/** Compare headings the way a person would: ignore case, punctuation, spacing. */
function normalize(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

/**
 * @param doc   the activity's document (same-origin, or this cannot work)
 * @returns a handle, or null when the activity has no sections we recognise
 */
export function installLockstep(doc: Document): LockstepHandle | null {
  const sections = findSlides(doc);
  if (sections.length < 2) return null;

  let currentIndex = -1;

  const stageIdOf = (el: HTMLElement) => el.dataset.stage ?? el.id ?? "";

  /** The section's own heading, which is what the teacher's stage list shows. */
  const headingOf = (el: HTMLElement) =>
    normalize(el.querySelector("h1, h2, h3, h4")?.textContent ?? "");

  const headings = sections.map(headingOf);

  /**
   * Most decks show one slide with a class -- .active, .current, .show -- and
   * hide the rest in their own stylesheet. Un-hiding an element is therefore
   * not enough: the deck's CSS still hides it, and the student sees a blank
   * screen or the deck's own idea of the current slide, neither of which is
   * the teacher's stage. So we move the deck's class as well as the display.
   */
  const ACTIVE_CLASSES = ["active", "current", "show", "visible", "is-active", "selected"];
  const activeClass = (() => {
    for (const name of ACTIVE_CLASSES) {
      const count = sections.filter((el) => el.classList.contains(name)).length;
      if (count === 1) return name;   // exactly one slide has it: that's the convention
    }
    return null;
  })();

  /**
   * True while apply() is writing, so the watchdog never reacts to us.
   *
   * apply() sets style and class -- the very attributes the observer watches.
   * Left unguarded that is not a loop that eventually settles: observer
   * callbacks are microtasks, and a microtask that queues another microtask
   * starves the event loop outright. The tab stops rendering, timers stop
   * firing and WebSocket messages stop being delivered, so the student sat
   * frozen on "Waiting for your teacher" while the class moved on, and only a
   * fresh page load -- rejoining -- ever showed them the right slide.
   */
  let applying = false;
  let observer: MutationObserver | null = null;

  function apply() {
    if (applying) return;
    applying = true;
    // Our own writes must not be observed. disconnect() also discards records
    // already queued, so re-observing below starts from a clean slate.
    observer?.disconnect();
    try {
      write();
    } finally {
      observer?.observe(doc.body, OBSERVE_OPTIONS);
      applying = false;
    }
  }

  function write() {
    sections.forEach((el, i) => {
      const shouldShow = i === currentIndex;
      if (shouldShow) {
        if (activeClass) el.classList.add(activeClass);
        el.removeAttribute("aria-hidden");
        el.style.removeProperty("display");
        // If the deck's own CSS still hides it, override -- but keep whatever
        // layout mode it wanted (flex, grid) rather than forcing block.
        const computed = el.ownerDocument.defaultView?.getComputedStyle(el);
        if (!computed || computed.display === "none") {
          el.style.setProperty("display", el.dataset.lismDisplay || "block", "important");
        }
        el.style.setProperty("visibility", "visible", "important");
        el.style.removeProperty("opacity");
      } else {
        if (activeClass) el.classList.remove(activeClass);
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
  //
  // Re-assertion is deliberately deferred through a timer rather than run
  // straight from the callback. A timer is a macrotask, so rendering, timers
  // and socket messages all get their turn between passes: even an activity
  // that fights back in a loop can only make this slow, never make the tab
  // unresponsive. The delay also coalesces a burst of mutations into one pass.
  let pending: ReturnType<typeof setTimeout> | null = null;
  observer = new MutationObserver(() => {
    if (applying || pending) return;
    pending = setTimeout(() => {
      pending = null;
      apply();
    }, WATCHDOG_DELAY_MS);
  });
  observer.observe(doc.body, OBSERVE_OPTIONS);

  return {
    showStage(stageId, index, label) {
      // Three ways to find the section, best evidence first.
      //
      // Position used to be the immediate fallback, and it is the one that
      // can be confidently, silently wrong: it only holds while the stage
      // list and the document agree on how many sections exist. When a
      // worksheet's opening section was missing from the list, every stage
      // landed a section early -- the class read the Starter while the
      // teacher's ten-minute Knowledge Box clock ran.
      //
      // Matching the heading closes that gap without anyone re-uploading
      // anything: the teacher's stage list is built from these very headings,
      // so "Section 3 - Starter / Retrieval" finds its own section whatever
      // the ids happen to be.
      const byId = stageId ? sections.findIndex((el) => stageIdOf(el) === stageId) : -1;

      let byHeading = -1;
      const wanted = normalize(label ?? "");
      if (byId < 0 && wanted.length >= 4) {
        byHeading = headings.findIndex((h) => h === wanted);
        if (byHeading < 0) {
          // A label truncated for the teacher's list still identifies its
          // section. Length-guarded so a short word cannot match everything.
          byHeading = headings.findIndex(
            (h) => h.length >= 4 && (h.startsWith(wanted) || wanted.startsWith(h))
          );
        }
      }

      const matched = byId >= 0 ? byId : byHeading;
      currentIndex = matched >= 0 ? matched : Math.min(index, sections.length - 1);
      if (stageId === null) currentIndex = -1;
      apply();
    },
    destroy() {
      if (pending) clearTimeout(pending);
      pending = null;
      observer?.disconnect();
      doc.removeEventListener("keydown", keyGuard, true);
      doc.removeEventListener("touchmove", touchGuard, true);
    },
  };
}
