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
const DESIGN_HEIGHT = 760;

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

  /** Point the preview at whatever stage the teacher has running. */
  const apply = useCallback(() => {
    if (!lockstepRef.current) return;
    const target = stage ? stage.anchor || stage.id : null;
    lockstepRef.current.showStage(running ? target : null, stageIndex, stage?.label);
  }, [stage, stageIndex, running]);

  useEffect(apply, [apply]);

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
          <div
            ref={boxRef}
            className="relative mt-4 overflow-hidden rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-950"
            style={{ height: DESIGN_HEIGHT * scale }}
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
                height: DESIGN_HEIGHT,
                transform: `scale(${scale})`,
                transformOrigin: "top left",
                // A mirror, not a second copy to interact with. Without this a
                // teacher could type into it and wonder where the answer went.
                pointerEvents: "none",
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
