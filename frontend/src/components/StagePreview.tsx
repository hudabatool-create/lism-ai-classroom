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

interface Props {
  activityId: string;
  /** The stage the teacher has started, or null when none is running. */
  stage: Stage | null;
  /** Its position in the stage list -- the last-resort way to find it. */
  stageIndex: number;
  running: boolean;
}

export default function StagePreview({ activityId, stage, stageIndex, running }: Props) {
  const [open, setOpen] = useState(true);
  const [scale, setScale] = useState(0.4);
  const [loaded, setLoaded] = useState(false);
  const [contentHeight, setContentHeight] = useState(FALLBACK_HEIGHT);
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

  // Scale the full-width activity down to whatever room the panel has, rather
  // than showing a cropped corner of it.
  useEffect(() => {
    const box = boxRef.current;
    if (!box || !open) return;
    const fit = () => setScale(Math.min(1, box.clientWidth / DESIGN_WIDTH));
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

    const measured =
      section && view
        ? section.getBoundingClientRect().bottom + (view.scrollY || 0) + 24
        : Math.max(doc.documentElement?.scrollHeight ?? 0, doc.body?.scrollHeight ?? 0);

    const height = Math.max(measured, 240);
    // Resizing the iframe changes the document's own layout, which the
    // observer then reports back. Ignoring small differences stops that
    // becoming a loop that never settles.
    setContentHeight((current) => (Math.abs(current - height) > 8 ? height : current));
  }, []);

  /** Point the preview at whatever stage the teacher has running. */
  const apply = useCallback(() => {
    if (!lockstepRef.current) return;
    const target = stage ? stage.anchor || stage.id : null;
    lockstepRef.current.showStage(running ? target : null, stageIndex, stage?.label);
    // After the new section is on screen, not before -- its height is the
    // thing that just changed.
    requestAnimationFrame(measure);
  }, [stage, stageIndex, running, measure]);

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
      apply();
    } catch {
      setPinned(false);
    }
  };

  useEffect(() => () => lockstepRef.current?.destroy(), []);

  const scaledHeight = contentHeight * scale;
  const scrolls = running && scaledHeight > MAX_PANEL_HEIGHT + 8;

  return (
    <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-white">
            What students are seeing
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {running && stage
              ? `Everyone is on ${stage.label}.`
              : "No stage running — every student's screen is covered."}
          </p>
        </div>
        <button
          onClick={toggle}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {open ? "Hide" : "Show"}
        </button>
      </div>

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
              running ? "overflow-y-auto" : "overflow-hidden"
            }`}
            style={{ height: running ? Math.min(scaledHeight, MAX_PANEL_HEIGHT) : 180 }}
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
                width: DESIGN_WIDTH,
                height: contentHeight,
                transform: `scale(${scale})`,
                transformOrigin: "top left",
                // A mirror, not a second copy to interact with. Without this a
                // teacher could type into it and wonder where the answer went.
                pointerEvents: "none",
                // The scaled box is what the scroll container must measure
                // against; the untransformed height would leave a long gap
                // below the section.
                marginBottom: contentHeight * (scale - 1),
              }}
            />
            {!running && loaded && (
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
