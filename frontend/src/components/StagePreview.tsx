"use client";

/**
 * What the class is looking at, on the teacher's own screen.
 *
 * A teacher running a lesson has no way to check that students are seeing what
 * they think they are seeing, short of walking to a desk or turning to the
 * projector. This mirrors the stage they started, pinned the same way the
 * student page pins it -- same proxy, same lockstep, same matching -- so what
 * shows here is what shows there, not a second guess at it.
 *
 * Deliberately not interactive: clicks and typing are switched off. This is a
 * mirror, not a second copy of the lesson to fiddle with. The teacher's
 * controls are the stage buttons above it.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { installLockstep, type LockstepHandle } from "@/lib/lockstep";
import type { Stage } from "@/lib/types";

/** The width the activity is laid out at before being scaled down to fit. */
const DESIGN_WIDTH = 1100;
/** Before the real section has been measured. */
const FALLBACK_HEIGHT = 760;
/** How much of the dashboard the panel may take before it scrolls instead. */
const MAX_PANEL_HEIGHT = 460;
/** How long to let the frame stop moving before showing it again. */
const SETTLE_MS = 160;

interface Props {
  activityId: string;
  /** The stage the teacher has started, or null when none is running. */
  stage: Stage | null;
  /** Its position in the stage list -- the last-resort way to find it. */
  stageIndex: number;
  running: boolean;
  /** Every stage, so the teacher can look back at one they have already run. */
  stages: Stage[];
  /** False when the activity never reports its own marks. */
  reportsMarks?: boolean;
  /** How far the lesson has got; nothing beyond this can be looked at. */
  currentStageIndex: number;
}

export default function StagePreview({
  activityId,
  stage,
  stageIndex,
  running,
  stages,
  currentStageIndex,
  reportsMarks,
}: Props) {
  /**
   * A stage the teacher is looking back at, or null for the live one.
   *
   * Looking back changes nothing for anybody else: no broadcast, no stage
   * change, no timer. The class carries on exactly as it was. That is what
   * makes this the safe way to check what an earlier slide said -- the worst
   * it can do is show the wrong slide on the teacher's own screen.
   */
  const [lookingAt, setLookingAt] = useState<string | null>(null);
  const reviewed = lookingAt ? (stages.find((s) => s.id === lookingAt) ?? null) : null;
  const reviewedIndex = reviewed ? stages.findIndex((s) => s.id === reviewed.id) : -1;

  // What the panel is actually showing, live stage or looked-back one.
  const shownStage = reviewed ?? stage;
  const shownIndex = reviewed ? reviewedIndex : stageIndex;
  const shownRunning = reviewed ? true : running;

  const [open, setOpen] = useState(true);
  const [boxWidth, setBoxWidth] = useState(DESIGN_WIDTH);
  const [loaded, setLoaded] = useState(false);
  const [contentHeight, setContentHeight] = useState(FALLBACK_HEIGHT);
  // The panel is hidden while the frame is being sized, so the two or three
  // reflows it takes are never seen -- one fade instead of a jumping box.
  const [settling, setSettling] = useState(false);
  const heightRef = useRef(FALLBACK_HEIGHT);
  const settleRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Heights already tried for the current stage -- see measure(). */
  const triedRef = useRef<Set<number>>(new Set());
  // null until the iframe loads; false means the activity has no sections we
  // can recognise, which the teacher needs told rather than left to infer
  // from a preview that shows the whole lesson at once.
  const [pinned, setPinned] = useState<boolean | null>(null);

  const boxRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const lockstepRef = useRef<LockstepHandle | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem("lism_stage_preview_open");
    if (saved !== null) setOpen(saved === "1");
  }, []);

  const toggle = () => {
    setOpen((wasOpen) => {
      localStorage.setItem("lism_stage_preview_open", wasOpen ? "0" : "1");
      return !wasOpen;
    });
  };

  useEffect(() => {
    const box = boxRef.current;
    if (!box || !open) return;
    const fit = () => setBoxWidth(box.clientWidth);
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(box);
    return () => observer.disconnect();
  }, [open]);

  /** How tall the section actually is, so nothing is cut off unreachably.
   *
   * Sections are wildly different heights -- a two-line objective slide and a
   * Knowledge Box with a worked example are not the same shape. A fixed box
   * clipped the tall ones with no way to reach the rest of them.
   */
  /** Tell React the height once the frame has stopped changing. */
  const commitHeight = useCallback(() => {
    if (settleRef.current) clearTimeout(settleRef.current);
    settleRef.current = null;
    setContentHeight(heightRef.current);
    setSettling(false);
  }, []);

  const measure = useCallback(() => {
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;
    // The section's own bottom edge, not the document's. The document also
    // holds a sticky header and the page's own bottom padding, so measuring
    // it made a two-line objectives slide reserve as much room as a Knowledge
    // Box -- every section came out the same height, which is the thing this
    // was meant to stop.
    const section = lockstepRef.current?.currentSection();
    const view = doc.defaultView;

    // How much is being hidden behind a scrollbar right now -- in the section,
    // in anything scrolling inside it, or in the document.
    //
    // Growing by exactly this much converges: each pass reveals what was
    // hidden, and once nothing is hidden it stops. Measuring the box instead
    // could not work for a deck whose slides are a full screen tall, because
    // the box is the frame by definition -- it reported "taller than the
    // frame" however tall the frame got, and grew until it hit a hard cap.
    const overflowOf = (el: Element) => Math.max(0, el.scrollHeight - el.clientHeight);
    let hidden = overflowOf(doc.documentElement);
    if (section) {
      hidden = Math.max(hidden, overflowOf(section));
      section.querySelectorAll("*").forEach((el) => {
        if (el.clientHeight > 40) hidden = Math.max(hidden, overflowOf(el));
      });
    }

    // Nothing hidden: the section's own bottom edge is the honest height, and
    // that is what lets a short section show a short panel.
    const bottom =
      section && view
        ? section.getBoundingClientRect().bottom + (view.scrollY || 0)
        : Math.max(doc.documentElement?.scrollHeight ?? 0, doc.body?.scrollHeight ?? 0);

    const current = heightRef.current;
    let target: number;
    if (hidden > 8) {
      target = current + hidden;
    } else {
      // The gutter goes on only when the section ends short of the frame.
      // A slide sized to the whole screen ends exactly at the frame, so
      // adding to it grew the frame every single pass -- which is how this
      // ran to its limit twice, leaving a screen of nothing to scroll past.
      target = bottom + (bottom < current - 24 ? 24 : 0);
    }
    const height = Math.min(Math.max(target, 240), 6000);
    // Resizing the frame relayouts the document, which the observer reports
    // straight back. Ignoring small differences stops that becoming a loop.
    if (Math.abs(current - height) <= 8) {
      commitHeight();
      return;
    }

    // A height we have already been at this stage means we are going round in
    // a circle, so stop and keep the taller one.
    //
    // Some decks size themselves to the window -- body{height:100vh} with the
    // slide filling what the fixed bars leave. The section's bottom edge is
    // then always the same distance below the frame however tall the frame
    // gets, so measuring it asks the frame to shrink, and shrinking hides
    // content, which asks it to grow again. A real Grade 5 Arabic deck sat
    // there swapping between 416px and 348px several times a second for as
    // long as the stage was running, and the teacher had that going on beside
    // them while trying to teach.
    //
    // Neither number is wrong; the deck simply has no fixed height to find.
    // The taller one is the one that hides nothing, so that is the answer.
    if (triedRef.current.has(height)) {
      heightRef.current = Math.max(current, height);
      if (iframeRef.current) iframeRef.current.style.height = `${heightRef.current}px`;
      commitHeight();
      return;
    }
    triedRef.current.add(height);

    // Resize the frame itself, without telling React.
    //
    // Converging takes two or three passes, and putting each one through state
    // re-rendered the panel every time -- so starting a stage made the whole
    // preview jump repeatedly, which is what read as flickering. The steps now
    // happen on the element alone, and React is told once, at the end.
    heightRef.current = height;
    if (iframeRef.current) iframeRef.current.style.height = `${height}px`;
    if (settleRef.current) clearTimeout(settleRef.current);
    settleRef.current = setTimeout(commitHeight, SETTLE_MS);
  }, [commitHeight]);

  /** Point the preview at whatever stage the teacher has running. */
  const apply = useCallback(() => {
    if (!lockstepRef.current) return;
    const target = shownStage ? shownStage.anchor || shownStage.id : null;
    setSettling(true);
    // A new section is a new shape, so last section's heights say nothing
    // about this one.
    triedRef.current.clear();
    lockstepRef.current.showStage(shownRunning ? target : null, shownIndex, shownStage?.label);
    // After the new section is on screen, not before -- its height is the
    // thing that just changed.
    requestAnimationFrame(measure);
    // A section that needs no resizing would never reach commitHeight, so the
    // panel would stay hidden. Reveal it regardless after the settle window.
    if (settleRef.current) clearTimeout(settleRef.current);
    settleRef.current = setTimeout(commitHeight, SETTLE_MS);
  }, [shownStage, shownIndex, shownRunning, measure, commitHeight]);

  useEffect(apply, [apply]);

  // The section can also grow on its own: a model answer unfolds, an image
  // finishes loading. Keep the panel honest about how much there is to see.
  useEffect(() => {
    const doc = iframeRef.current?.contentDocument;
    if (!doc?.body || !loaded) return;
    const observer = new ResizeObserver(measure);
    observer.observe(doc.body);
    return () => observer.disconnect();
  }, [loaded, measure]);

  const handleLoad = () => {
    setLoaded(true);
    try {
      const doc = iframeRef.current?.contentDocument;
      if (!doc) return;
      lockstepRef.current?.destroy();
      lockstepRef.current = installLockstep(doc);
      setPinned(lockstepRef.current !== null);

      // The activity's own scrollbar is a dead control here: the frame ignores
      // mouse input, so it cannot be dragged, and the only thing past the
      // section is the page's own blank bottom padding. Two bars, one of which
      // does nothing, reads as a preview that has frozen. The panel outside
      // owns all the scrolling.
      doc.documentElement.style.overflow = "hidden";
      if (doc.body) doc.body.style.overflow = "hidden";

      apply();
    } catch {
      setPinned(false);
    }
  };

  useEffect(
    () => () => {
      lockstepRef.current?.destroy();
      if (settleRef.current) clearTimeout(settleRef.current);
    },
    []
  );

  // On a wide dashboard, lay the activity out at the panel's own width rather
  // than at 1100px with dead space beside it. On a narrow one there is no room
  // to do that, so lay it out at 1100 and scale the whole thing down to fit.
  const roomy = boxWidth >= DESIGN_WIDTH;
  const frameWidth = roomy ? boxWidth : DESIGN_WIDTH;
  const scale = roomy ? 1 : boxWidth / DESIGN_WIDTH;

  const scaledHeight = contentHeight * scale;
  const scrolls = shownRunning && scaledHeight > MAX_PANEL_HEIGHT + 8;

  return (
    <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-white">
            {reviewed ? "Looking back" : "What students are seeing"}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {reviewed
              ? `${reviewed.label} — students have not moved.`
              : running && stage
                ? `Everyone is on ${stage.label}.`
                : "No stage running — every student's screen is covered."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Only stages the class has already reached. Looking back is safe
              precisely because it changes nothing; letting a teacher look
              *forward* would put an unstarted slide on a screen that says
              "what students are seeing", which is the opposite of the point. */}
          <select
            value={lookingAt ?? ""}
            onChange={(e) => setLookingAt(e.target.value || null)}
            className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
          >
            <option value="">Live — follow the class</option>
            {stages.slice(0, Math.max(currentStageIndex + 1, 0)).map((s) => (
              <option key={s.id} value={s.id}>
                Look back at {s.label}
              </option>
            ))}
          </select>
          <button
            onClick={toggle}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {open ? "Hide" : "Show"}
          </button>
        </div>
      </div>

      {reviewed && (
        <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
          You are looking at an earlier stage. Nothing has changed for your students &mdash; they
          are still on {stage ? stage.label : "the waiting screen"}.{" "}
          <button onClick={() => setLookingAt(null)} className="font-semibold underline">
            Back to live
          </button>
        </p>
      )}

      {open && (
        <>
          {/* Scrolls rather than clipping. The iframe is sized to the whole
              section and this box caps how much of the dashboard it takes, so
              a long section -- a Knowledge Box with a worked example -- can be
              read to the end instead of being cut off at a fixed height.
              Because the iframe ignores pointer events, the wheel lands here,
              which is what makes scrolling work without making the preview
              something the teacher can type into. */}
          <div
            ref={boxRef}
            className={`relative mt-4 overflow-x-hidden rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-950 ${
              shownRunning ? "overflow-y-auto" : "overflow-hidden"
            }`}
            style={{ height: shownRunning ? Math.min(scaledHeight, MAX_PANEL_HEIGHT) : 180 }}
          >
            <iframe
              ref={iframeRef}
              // Same origin as the student's copy, which is what lets the
              // preview be pinned to a stage at all.
              src={`/activity/${activityId}/raw`}
              onLoad={handleLoad}
              title="Preview of the stage students are on"
              className="border-0"
              style={{
                width: frameWidth,
                height: contentHeight,
                transform: `scale(${scale})`,
                transformOrigin: "top left",
                // A mirror, not a second copy to interact with. Without this a
                // teacher could type into it and wonder where the answer went.
                pointerEvents: "none",
                opacity: settling ? 0 : 1,
                transition: "opacity 140ms ease",
                // The scaled box is what the scroll container must measure
                // against; the untransformed height would leave a long gap
                // below the section.
                marginBottom: contentHeight * (scale - 1),
              }}
            />
            {!shownRunning && loaded && (
              <div className="absolute inset-0 flex items-center justify-center bg-slate-900/60 text-center text-sm font-medium text-white">
                Students see &ldquo;Waiting for your teacher&rdquo;
                <br />
                until you start a stage.
              </div>
            )}
            {!loaded && (
              <p className="absolute inset-0 flex items-center justify-center text-xs text-slate-400">
                Loading the activity&hellip;
              </p>
            )}
          </div>

          {scrolls && (
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              This section is longer than the panel &mdash; scroll inside it to see the rest.
              Students see the whole section on their own screens.
            </p>
          )}

          {reportsMarks === false && (
            // The activity marks itself but never tells LISM, so every mark
            // will land as "awaiting your review". Said before the lesson,
            // this is a five-second expectation; discovered afterwards, it is
            // thirty students marked by hand with no explanation.
            <p className="mt-3 rounded-lg bg-sky-50 px-3 py-2 text-xs text-sky-900 dark:bg-sky-950 dark:text-sky-200">
              This activity does not send its marks to LISM, so every answer will arrive for you
              to mark rather than scored automatically. Everything else works normally &mdash;
              answers, timing and the report are unaffected.
            </p>
          )}

          {pinned === false && (
            // Worth saying out loud: this is the one case where LISM cannot
            // hold students on a stage, and silently doing nothing looks
            // exactly like the feature working.
            <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              LISM could not find separate sections in this activity, so students see all of it at
              once and stage locking does not apply. Starting and ending stages still paces the
              class and still times them.
            </p>
          )}
        </>
      )}
    </div>
  );
}
