/**
 * Reading a student's answer out of an activity that never reports its own.
 *
 * Run:  node src/lib/harvest.test.mjs
 *
 * The markup here is lifted from a worksheet a teacher actually generated
 * elsewhere and uploaded: it validates the answer, prints "Answer accepted!"
 * and posts nothing back, so the teacher's live feed stayed empty however
 * many times they refreshed.
 */
import { JSDOM } from "jsdom";
import { collectAnswers, watchSubmits } from "./harvest.ts";

const results = [];
function check(label, ok, detail = "") {
  results.push(!!ok);
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}`);
  if (detail) console.log(`      ${detail}`);
}

const HTML = `<!DOCTYPE html><html><body>
  <section class="card" id="sec-1">
    <h2>Section 1 · Worksheet Details</h2>
    <label class="input-label" for="student-name">Student Name:</label>
    <input type="text" id="student-name" class="short-input" value="Amina Hassan">
    <label class="input-label" for="student-class">Class / Section:</label>
    <input type="text" id="student-class" value="9-A">
  </section>

  <section class="card starter-card" id="sec-3">
    <h2>Section 3 · Starter / Retrieval</h2>
    <div class="input-group">
      <label class="input-label" for="starter-q1">1. Identify the Python data types of 45, 3.14, "Grade 9" and True.</label>
      <textarea id="starter-q1" class="prose-input" data-type="prose">45 is an int, 3.14 is a float, "Grade 9" is a str and True is a bool.</textarea>
    </div>
    <button class="btn btn-sm" onclick="validateBox('starter-q1')">Submit Starter Answer</button>
    <div class="model-toggle" id="model-starter-q1">
      <div class="model-header"><span>Submit your answer first</span></div>
      <div class="model-content">Model Answer: int, float, str, bool.</div>
    </div>
  </section>

  <section class="card" id="sec-8">
    <h2>Section 8 · Exit Ticket</h2>
    <div class="input-group">
      <label class="input-label" for="exit-input">What is the output of the code?</label>
      <input type="text" id="exit-input" value="5">
    </div>
    <div class="input-group">
      <label class="input-label" for="conf">How confident are you?</label>
      <select id="conf"><option value="">Choose…</option><option value="2" selected>Fairly confident</option></select>
    </div>
    <button class="btn" onclick="validateExit()">Submit Exit Ticket</button>
  </section>

  <section class="card" id="sec-9">
    <h2>Section 9 · Nothing Typed</h2>
    <div class="input-group">
      <label class="input-label" for="empty-q">Your reflection</label>
      <textarea id="empty-q"></textarea>
    </div>
  </section>
</body></html>`;

const dom = new JSDOM(HTML, { pretendToBeVisual: true });
const doc = dom.window.document;
global.CSS = dom.window.CSS;
// jsdom has no layout, so offsetParent is always null. Treat every element as
// laid out; lockstep is what actually decides which section is on screen.
Object.defineProperty(dom.window.HTMLElement.prototype, "offsetParent", {
  get() { return this.ownerDocument.body; },
});

// --- the Starter, which is what the teacher said was missing ---------------
const starter = collectAnswers(doc.querySelector("#sec-3"), doc);
check("the Starter answer is captured at all", starter.filled === 1, `filled: ${starter.filled}`);
check("the exact text the student typed is captured",
  starter.text.includes('45 is an int, 3.14 is a float, "Grade 9" is a str and True is a bool.'),
  starter.text);
check("the question is captured with the answer",
  starter.text.includes("Identify the Python data types"),
  "a teacher scanning the feed must know which question it answers");
check("the model answer is not swept up as the student's",
  !starter.text.includes("Model Answer"), starter.text);

// --- several fields, and a dropdown ----------------------------------------
const exit = collectAnswers(doc.querySelector("#sec-8"), doc);
check("every answered field in the section is captured", exit.filled === 2, `filled: ${exit.filled}`);
check("the typed answer is there", exit.text.includes("5"), exit.text);
check("a dropdown reports the visible choice, not its value",
  exit.text.includes("Fairly confident") && !exit.text.includes("→ 2"), exit.text);

// --- what must NOT be reported ---------------------------------------------
const details = collectAnswers(doc.querySelector("#sec-1"), doc);
check("the student's name and class are not reported as an answer",
  details.filled === 0, details.text);

const untouched = collectAnswers(doc.querySelector("#sec-9"), doc);
check("a section the student left blank reports nothing",
  untouched.filled === 0,
  "blank must never be sent -- it would read as an answer that was given");

// --- the submit button ------------------------------------------------------
let fired = 0;
const stop = watchSubmits(doc, () => { fired += 1; });

doc.querySelector("#sec-3 button").dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
await new Promise((r) => setTimeout(r, 20));
check("pressing the activity's own Submit is noticed", fired === 1, `fired ${fired}×`);

doc.querySelector("#model-starter-q1 .model-header").dispatchEvent(
  new dom.window.MouseEvent("click", { bubbles: true }));
await new Promise((r) => setTimeout(r, 20));
check("clicking something that isn't a submit control does nothing",
  fired === 1, `fired ${fired}×`);

stop();
doc.querySelector("#sec-8 button").dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
await new Promise((r) => setTimeout(r, 20));
check("the watcher stops cleanly", fired === 1, `fired ${fired}×`);


// ---------------------------------------------------------------------------
// An Arabic lesson must report answers like any other.
//
// Submit detection was English-only, so a Grade 5 Arabic deck whose button
// reads "إرسال" reported nothing at all: the teacher's panel showed
// "0 of 1 answered" for a class that had answered everything. In a bilingual
// school that is not an edge case.
// ---------------------------------------------------------------------------
const ARABIC = `<!DOCTYPE html><html lang="ar" dir="rtl"><body>
  <section data-stage="starter">
    <h3>ما الفرق بين الاسم والفعل؟</h3>
    <textarea id="s1">الطالبُ اسم و يكتبُ فعل</textarea>
    <h3>حدّد نوع الكلمة: «المدرسةُ»</h3>
    <select id="s2"><option value="">اختر</option><option selected>اسم</option><option>فعل</option></select>
    <button onclick="checkStarter()">إرسال التهيئة</button>
  </section>
</body></html>`;

const dom6 = new JSDOM(ARABIC, { pretendToBeVisual: true });
const doc6 = dom6.window.document;
global.CSS = dom6.window.CSS;
Object.defineProperty(dom6.window.HTMLElement.prototype, "offsetParent", {
  get() { return this.ownerDocument.body; },
});

let arabicFired = 0;
const stopAr = watchSubmits(doc6, () => { arabicFired += 1; });
doc6.querySelector("button").dispatchEvent(new dom6.window.MouseEvent("click", { bubbles: true }));
await new Promise((r) => setTimeout(r, 20));
check('an Arabic submit button ("إرسال") is recognised', arabicFired === 1, `fired ${arabicFired}×`);

const ar = collectAnswers(doc6.querySelector('[data-stage="starter"]'), doc6);
check("the Arabic written answer is captured", ar.text.includes("الطالبُ اسم"), ar.text.slice(0, 40));
check("the Arabic dropdown choice is captured", ar.text.includes("اسم"), ar.text.slice(0, 60));
check("both Arabic fields counted", ar.filled === 2, `filled: ${ar.filled}`);
stopAr();

// A button that is not a submit, in Arabic, must still be ignored.
let strayAr = 0;
const stopAr2 = watchSubmits(doc6, () => { strayAr += 1; });
const stray = doc6.createElement("button");
stray.textContent = "مسح";           // "clear"
doc6.body.appendChild(stray);
stray.dispatchEvent(new dom6.window.MouseEvent("click", { bubbles: true }));
await new Promise((r) => setTimeout(r, 20));
check("an Arabic non-submit button is ignored", strayAr === 0, `fired ${strayAr}×`);
stopAr2();

const passed = results.filter(Boolean).length;
console.log(`\nTOTAL ${passed} passed, ${results.length - passed} failed`);
process.exit(results.every(Boolean) ? 0 : 1);
