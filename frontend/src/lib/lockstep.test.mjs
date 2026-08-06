/**
 * Lockstep against a deliberately uncooperative deck.
 *
 * The fixture is the case that matters: a deck with its own Next button, its
 * own arrow-key handler, and no idea LISM exists. If enforcement only worked
 * on well-behaved activities it would be worth nothing.
 *
 *   node --experimental-strip-types src/lib/lockstep.test.mjs
 */
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import { installLockstep } from "./lockstep.ts";

const HTML = `<!DOCTYPE html><html><body>
  <div class="slide-nav">
    <button class="prev">Previous</button>
    <span class="slide-counter">1 / 4</span>
    <button class="next">Next</button>
  </div>
  <section data-stage="starter"><h2>Starter</h2><input id="a"></section>
  <section data-stage="main-activity"><h2>Main Activity</h2></section>
  <section data-stage="exit-ticket"><h2>Exit Ticket</h2></section>
  <section data-stage="reflection"><h2>Reflection</h2></section>
  <button id="submit">Submit answer</button>
</body></html>`;

const dom = new JSDOM(HTML, { pretendToBeVisual: true });
const doc = dom.window.document;
global.MutationObserver = dom.window.MutationObserver;

const results = [];
const check = (name, ok, detail = "") => {
  results.push(ok);
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? `\n      ${detail}` : ""}`);
};

const visible = () =>
  [...doc.querySelectorAll("section")]
    .filter((s) => s.style.display !== "none")
    .map((s) => s.dataset.stage);

const lock = installLockstep(doc);
check("installs on a deck with sections", lock !== null);

// --- nothing running: the student must see no slide at all ---------------
lock.showStage(null, -1);
check("no stage running shows nothing", visible().length === 0, `visible: ${visible()}`);

// --- teacher starts the starter ------------------------------------------
lock.showStage("starter", 0);
check("teacher's stage is the only one visible", JSON.stringify(visible()) === '["starter"]', `visible: ${visible()}`);

// --- the deck's own navigation is gone ------------------------------------
const hidden = (sel) => doc.querySelector(sel)?.style.display === "none";
check("Next button hidden", hidden(".next"));
check("Previous button hidden", hidden(".prev"));
check("slide counter hidden", hidden(".slide-counter"));
check("Submit is NOT hidden", doc.querySelector("#submit").style.display !== "none",
  "hiding Submit would stop students answering");

// --- the deck tries to move itself; the watchdog must undo it -------------
const exit = doc.querySelector('[data-stage="exit-ticket"]');
exit.style.display = "block";
await new Promise((r) => setTimeout(r, 30));   // let MutationObserver fire
check("a slide the deck reveals is snapped back",
  JSON.stringify(visible()) === '["starter"]', `visible: ${visible()}`);

// --- arrow keys must not reach the deck's handler -------------------------
let deckSawArrow = false;
doc.addEventListener("keydown", (e) => { if (e.key === "ArrowRight") deckSawArrow = true; });
doc.body.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
check("arrow key blocked before the deck sees it", deckSawArrow === false);

// --- but typing must still work -------------------------------------------
let inputSawKey = false;
const input = doc.querySelector("#a");
input.addEventListener("keydown", () => { inputSawKey = true; });
input.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
check("arrow keys still work inside an input", inputSawKey === true,
  "students must be able to edit what they typed");

// --- moving on ------------------------------------------------------------
lock.showStage("exit-ticket", 2);
check("teacher advancing moves every screen", JSON.stringify(visible()) === '["exit-ticket"]', `visible: ${visible()}`);

// --- an id the manifest and deck disagree on falls back to position -------
lock.showStage("does-not-exist", 1);
check("unknown stage id falls back to index", JSON.stringify(visible()) === '["main-activity"]', `visible: ${visible()}`);

// --- an activity we do not understand must be left alone ------------------
const plain = new JSDOM(`<!DOCTYPE html><html><body><div><p>A poster</p></div></body></html>`);
global.MutationObserver = plain.window.MutationObserver;
check("no recognisable sections -> does nothing", installLockstep(plain.window.document) === null,
  "better to leave an activity working than to blank it");

lock.destroy();


/* ---------------------------------------------------------------------
   The shape that was actually failing in the classroom: slides are DIVS
   inside a wrapper, with no data-stage, shown via an .active class and
   hidden by the deck's own stylesheet. The first version found no slides
   here at all and silently enforced nothing.
   --------------------------------------------------------------------- */
const REAL = `<!DOCTYPE html><html><head><style>
  .slide { display: none; }
  .slide.active { display: block; }
</style></head><body>
  <div class="deck">
    <div class="slide active" id="slide-1"><h2>Title</h2></div>
    <div class="slide" id="slide-2"><h2>Starter</h2></div>
    <div class="slide" id="slide-3"><h2>Main Activity</h2></div>
    <div class="slide" id="slide-4"><h2>Exit Ticket</h2></div>
  </div>
  <div class="slide-nav"><button class="next">Next</button></div>
</body></html>`;

const dom2 = new JSDOM(REAL, { pretendToBeVisual: true });
const doc2 = dom2.window.document;
global.MutationObserver = dom2.window.MutationObserver;

const lock2 = installLockstep(doc2);
check("finds div slides inside a wrapper", lock2 !== null,
  "this is the shape that silently failed before");

const shown = () =>
  [...doc2.querySelectorAll(".slide")]
    .filter((s) => s.classList.contains("active") && s.style.display !== "none")
    .map((s) => s.id);

lock2?.showStage(null, 2);          // teacher on slide 3, matched by index
lock2?.showStage("slide-3", 2);
check("moves the deck's own active class", JSON.stringify(shown()) === '["slide-3"]', `shown: ${shown()}`);
check("the deck's original slide is no longer active",
  doc2.querySelector("#slide-1").classList.contains("active") === false);
check("Next button hidden in the real shape",
  doc2.querySelector(".next").style.display === "none");

lock2?.showStage(null, -1);
check("nothing shown between stages", shown().length === 0, `shown: ${shown()}`);
lock2?.destroy();

const passed2 = results.filter(Boolean).length;
console.log(`\nTOTAL ${passed2} passed, ${results.length - passed2} failed`);
process.exit(results.every(Boolean) ? 0 : 1);
