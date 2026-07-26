# Master Prompt — Interactive HTML Worksheet (v7, all subjects)

**LISM-integrated · teacher-controlled pacing · pathway choice graded out of 10 · extension certificate instead of bonus marks**

> **What changed from v6** — the educational framework is unchanged. v7 makes the worksheet a first-class LISM AI Classroom activity: it emits a lesson manifest, reports every response to the teacher's live dashboard, hands pacing (start/pause/resume/end) to the teacher when used in class, adds a teacher preview mode, a student completion report, optional copy-paste protection and optional focus monitoring. It still opens standalone in any browser, works fully offline, prints on A4, and remains usable as self-paced homework.

Companion to the Interactive Lesson Deck prompt. Same lesson framework — keywords, ALL/MOST/SOME, DOK 1–4 worth 10 marks, connection link, exit ticket, reflection — but delivered as a single scrolling worksheet a student works through, rather than a presented deck.

Fill in: `[TOPIC NAME]` · `[SUBJECT]` · `[GRADE]` · `[WEEK X]` · `[PREVIOUS LESSON TOPIC]` (Leave keywords blank and write "guess the keywords yourself". Leave SUBJECT PROFILE values blank and Claude will infer them from the subject.)

---

Build a single self-contained interactive HTML worksheet for **[TOPIC NAME]** — [SUBJECT], Grade [GRADE], Week [WEEK X]. Previous lesson: [PREVIOUS LESSON TOPIC]. Guess the 5–6 lesson keywords yourself from the topic.

One HTML file, no required external dependencies, runs by opening the file in any browser, works offline, and works on a laptop, tablet and phone. Unlike a slide deck this is one continuous scrolling page divided into numbered sections, so a student can work through it independently, at their own pace, in class or as homework. Students type and submit answers directly into the worksheet. Designed for a 50-minute period, including 10 minutes reserved across the Starter, Main Task and Exit Ticket for teacher feedback and for students to explain or defend their work. It must also print cleanly on A4 as a paper worksheet.

The worksheet must run correctly in **three contexts**, with no separate build:

1. **Inside LISM AI Classroom, live in class** — embedded in an iframe, paced by the teacher, reporting live to the teacher dashboard (Sections 0 and 0b).
2. **Inside LISM as homework** — self-paced by the student, still reporting responses so the teacher sees them afterwards.
3. **Standalone** — opened from a file or link with no LISM present: self-paced, no reporting, fully offline, printable.

---

## 0. PACING — THE TEACHER CONTROLS TIME, NOT THE FILE (mandatory)

The worksheet contains **no timing mechanism of its own**. Do not build:

- Automatic timers in any section.
- JavaScript that starts a timer on first keystroke, focus, submission or any other student interaction.
- Countdown displays, clock faces, progress rings or timer UI of any kind.
- Auto-locking, greying out or disabling of inputs because time has passed.
- Time-based transitions between sections.
- Any logic that controls or enforces lesson pacing (no `setInterval`, `setTimeout` or `Date`-based gating **for pacing purposes** — `setTimeout` for a toast auto-hiding or an input debounce is fine).

Instead:

- Carry the recommended duration for every section as **metadata in the manifest** (`durationSeconds`, Section 0b).
- Print the recommended duration beside each section title as instructional guidance, e.g. `Section 3 · Starter · Recommended Duration: 5 minutes`.
- Inside LISM in class, the teacher controls **Start · Pause · Resume · End · Next section**, and LISM shows students the one synchronised countdown. The worksheet simply obeys the commands it is sent.
- In homework mode and standalone, the student self-paces and sees the recommended durations as guidance, plus the total expected time in the header.

The only permitted use of a timestamp is the completion time recorded in the downloaded answer file.

Everything else in this framework — activities, validation rules, DOK structure, scoring, keyword detection, sequential unlocking of model answers, the UAE/AI/Cross-Curricular section, reflection and overall lesson design — stays exactly as specified.

---

## 0b. LISM CLASSROOM INTEGRATION (mandatory)

This is what makes the worksheet a live LISM activity instead of an isolated page. **A worksheet that validates answers internally but never reports them will display perfectly and show the teacher nothing.**

### Detecting LISM

```js
const IN_LISM = window.parent !== window;
```

When false, run standalone: self-paced, emit nothing. When true, report events and accept pacing commands. The worksheet must never require LISM to function.

### The lesson manifest (required)

Emit exactly one inert JSON block in `<head>`, alongside (not instead of) the `PROFILE` object. LISM parses this server-side at upload, without running the page:

```html
<script type="application/json" id="lism-manifest">
{
  "lessonType": "worksheet",
  "subject": "[SUBJECT]",
  "grade": "[GRADE]",
  "week": "[WEEK X]",
  "topic": "[TOPIC NAME]",
  "learningObjectives": { "all": "…", "most": "…", "some": "…" },
  "keywords": ["…", "…", "…", "…", "…"],
  "dok": [
    { "level": 1, "label": "Recall",      "marks": 2 },
    { "level": 2, "label": "Skill",       "marks": 3 },
    { "level": 3, "label": "Application", "marks": 3 },
    { "level": 4, "label": "Evaluation",  "marks": 2 }
  ],
  "deliveryMode": "lesson",
  "sessionType": "lesson",
  "stages": [
    { "id": "header",           "label": "Header",                "type": "title",          "durationSeconds": 60,  "sequentialLock": false, "marks": null },
    { "id": "keywords",         "label": "Keywords & Objective",  "type": "keywords",       "durationSeconds": 120, "sequentialLock": false, "marks": null },
    { "id": "starter",          "label": "Starter / Retrieval",   "type": "starter",        "durationSeconds": 300, "sequentialLock": true,  "marks": null },
    { "id": "knowledge-box",    "label": "Knowledge Box",         "type": "teaching",       "durationSeconds": 300, "sequentialLock": true,  "marks": null },
    { "id": "guided-practice",  "label": "Guided Practice",       "type": "practice",       "durationSeconds": 300, "sequentialLock": true,  "marks": null },
    { "id": "main-task",        "label": "Main Task",             "type": "main-activity",  "durationSeconds": 600, "sequentialLock": true,  "marks": 10 },
    { "id": "mark-scheme",      "label": "Mark Scheme & Feedback","type": "rubric",         "durationSeconds": 120, "sequentialLock": true,  "marks": null },
    { "id": "connection",       "label": "Connection Link",       "type": "connection",     "durationSeconds": 180, "sequentialLock": true,  "marks": null },
    { "id": "exit-ticket",      "label": "Exit Ticket",           "type": "exit-ticket",    "durationSeconds": 300, "sequentialLock": true,  "marks": null },
    { "id": "reflection",       "label": "Reflection & Submit",   "type": "reflection",     "durationSeconds": 300, "sequentialLock": true,  "marks": null }
  ]
}
</script>
```

Rules: **one stage per numbered section, in order, ten stages for ten sections.** Ids must be stable, lowercase-hyphenated and unique — every event references a `stages[].id`, so a typo silently detaches that section from the dashboard. `durationSeconds` is the recommended duration only. `marks` is 10 on `main-task` and `null` elsewhere. Keep `deliveryMode` (`lesson` | `homework`, the worksheet's own wording axis, controlling whether the header shows total expected time) and `sessionType` (`lesson` | `practice` | `assessment`, LISM's enforcement axis) as two separate fields — **never merge them.** Give every section card a `data-stage="<id>"` attribute matching its manifest id.

### Commands LISM sends (parent → worksheet)

Listen on `window.addEventListener('message', …)` for `{ type: 'lism:command', command, … }`:

| `command` | Payload | The worksheet must |
|---|---|---|
| `start_stage` | `stage`, `stageIndex`, `serverTime` | Scroll to that section, highlight it as current, enable its inputs. In a scrolling document do **not** hide the other sections — the Knowledge Box must stay available as reference (Section 4) — but mark them as not-current |
| `stage_ended` | — | Show "Waiting for your teacher…" on that section and disable its inputs |
| `pause` | — | Freeze interaction, show a paused notice, keep every typed answer |
| `resume` | — | Unfreeze and restore the previous scroll position and view |
| `lock` | `reason` | Disable every input and show the reason; not dismissible by the student |
| `unlock` | — | Re-enable inputs (the teacher cleared the lock) |
| `set_config` | `copyPasteProtection`, `focusMonitoring`, `maxWarnings` | Apply teacher settings (Sections 0c and 0d) |
| `time_update` | `elapsedSeconds`, `remainingSeconds` | Store for the completion report; do not render a countdown |

**Ignore unknown commands silently** — never throw, never break. This lets LISM add commands later without regenerating the worksheet.

### Events the worksheet sends (worksheet → parent)

`window.parent.postMessage({ type: 'lism:event', event, … }, '*')`:

| `event` | Payload | When |
|---|---|---|
| `activity_ready` | `stageCount` | Once on load, inside LISM only |
| `stage_viewed` | `stageId` | A section scrolled into view or was jumped to (throttle — a scrolling page fires often) |
| `response_update` | `stageId`, `questionId`, `charCount`, `wordCount` | Student is typing — **throttle to at most once per 2 s per box**; never send keystrokes or answer text |
| `student_submitted` | `stageId`, `questionId`, `correct`, `answer`, `mark`, `maxMark`, `dok`, `rubricLevel`, `keywordsUsed` | A box was submitted **and accepted** |
| `stage_completed` | `stageId`, `marksEarned`, `maxMarks` | Every required box in that section is accepted |
| `activity_completed` | `pathway`, `totalMarks`, `maxMarks`, `stagesCompleted`, `keywordsUsed`, `extensionsCompleted`, `hintsUsed` | Reflection section completed / student pressed Finish |
| `help_requested` | `stageId`, `questionId` | Student clicked "I need help" in the worksheet |
| `focus_warning` | `stageId`, `warningNumber`, `kind` | The worksheet's own focus monitor fired (Section 0d) |

**`student_submitted` is the one event the live dashboard cannot work without.** Emit it for every accepted answer — Starter items, each Guided Practice item, each DOK question, each Exit Ticket item, each Reflection box — with `stageId` exactly matching the manifest id of the section it came from. Guided Practice submissions carry `mark: null` since they are not graded towards the 10.

### Reference implementation to include

```js
const IN_LISM = window.parent !== window;
const LISM = {
  config: { copyPasteProtection: false, focusMonitoring: false, maxWarnings: 3 },
  elapsedSeconds: null,
  preview: new URLSearchParams(location.search).get('preview') === '1',
  frozen: false,
  emit(event, payload = {}) {
    if (!IN_LISM || this.preview) return;   // preview never creates student data
    window.parent.postMessage({ type: 'lism:event', event, ...payload }, '*');
  }
};

window.addEventListener('message', (e) => {
  const d = e.data || {};
  if (d.type !== 'lism:command') return;
  switch (d.command) {
    case 'start_stage': focusSection(d.stage.id); break;
    case 'stage_ended': endSection(d.stage && d.stage.id); break;
    case 'pause':       setFrozen(true); break;
    case 'resume':      setFrozen(false); break;
    case 'lock':        applyLock(d.reason); break;
    case 'unlock':      clearLock(); break;
    case 'set_config':  Object.assign(LISM.config, d); applyConfig(); break;
    case 'time_update': LISM.elapsedSeconds = d.elapsedSeconds; break;
  }
});

if (IN_LISM) LISM.emit('activity_ready', { stageCount: STAGES.length });
```

Because the worksheet is served from a different origin than the LISM page, `postMessage` is the only channel — never assume shared DOM, cookies or storage.

---

## 0c. COPY & PASTE PROTECTION (teacher-configurable)

Off by default. Enabled by `set_config { copyPasteProtection: true }`. When on, **inside answer inputs only**:

- Block `copy`, `cut`, `paste`, `contextmenu` and text drag-and-drop.
- Show a short, calm notice: "Copy and paste are switched off for this worksheet — type your own answer."

Never disable keyboard navigation or browser accessibility features, and never block the whole page — the Knowledge Box and question text must stay selectable for reading aids. Where the subject profile uses `image` answers, keep the image-paste path working (a photograph of handwritten working is not plagiarism) unless the teacher's setting explicitly covers attachments. Standalone and in homework mode, protection is off unless LISM enables it.

---

## 0d. FOCUS MONITORING (teacher-configurable)

LISM runs its own focus monitor on the student page and owns the authoritative count, the lock and the teacher notification. The worksheet's monitor is secondary and must not duplicate authority:

- Monitor only when `set_config { focusMonitoring: true }`.
- Watch tab switching (`visibilitychange`) and window blur/focus.
- Collapse one physical departure into **one** warning — `blur` and `visibilitychange` both fire for the same event, so a naive implementation double-counts.
- Emit `focus_warning` with an incrementing `warningNumber` and show the student a warning.
- Maximum 3 warnings (`maxWarnings`). **Do not lock on your own authority** — LISM sends `lock` when the limit is reached, so there is one source of truth. Show the lock state and disable inputs when that command arrives.

---

## 0e. TEACHER PREVIEW MODE

Teachers review a worksheet before launching it, via `?preview=1` on the activity URL. When `preview` is true:

- Show **Previous / Next section** controls and a section counter ("4 / 10") in addition to the normal jump menu, so every section can be stepped through in order.
- Ignore `sequentialLock` entirely — every section reachable in any order.
- **Emit no events whatsoever** and create no student data (the `LISM.emit` guard above handles this).
- Show a clear banner: "Preview — not a live lesson. Nothing is recorded."
- Model answers and hints may be opened freely in preview, so the teacher can check them.

---

## 1. SUBJECT PROFILE (set this first — it drives all validation)

Before writing any HTML, state a subject profile as a JS config object at the top of the file, then build every answer box to obey it. Infer sensible values from [SUBJECT] and [TOPIC NAME]:

```js
const PROFILE = {
  subject:'[SUBJECT]', grade:'[GRADE]', week:'[WEEK X]', topic:'[TOPIC NAME]',
  lang:'en',            // 'en' | 'ar' | 'fr' | 'es' | 'ur' | 'hi' …
  dir:'ltr',            // 'rtl' for Arabic/Urdu — flips the whole layout
  math:false,           // true → math rendering + symbol palette
  chem:false,           // true → chemical formula & equation checking
  code:false,           // true → code editor behaviour + code-structure checking
  draw:false,           // true → sketch pad answer boxes enabled
  images:true,          // true → paste / upload / photograph an image into an answer
  mode:'lesson',        // 'lesson' (in class) | 'homework' (self-paced) — wording only, no timing logic
  defaultAnswerType:'prose'
};
```

The values here must agree with the manifest's `subject`, `grade`, `week`, `topic` and `deliveryMode` (`PROFILE.mode` and `deliveryMode` carry the same value).

**Answer types** — every response box declares one via `data-type`. Validation, feedback wording and marking all switch on it:

| `data-type` | Use for | Accepted when |
|---|---|---|
| `prose` | explanations, evaluation, reflection | min word count + min key-term matches + not gibberish |
| `numeric` | maths, physics, chemistry calculations | value matches answer key within tolerance, correct units if required |
| `symbolic` | algebra, formulae, expressions | normalised form matches any accepted form |
| `chem` | formulae and balanced equations | element-aware match, or atom counts balance both sides |
| `code` | programming | required structures/tokens present, not prose length |
| `short` | fill-in-the-blank, single terms, dates | matches answer key or accepted synonyms (normalised) |
| `checklist` | PE, Art, Design, practical/performance work | required boxes ticked + short justification meeting min words |
| `draw` | diagrams, graphs, circuits, labelled sketches, maps, free-body diagrams | canvas is not blank + required label list ticked + short caption meeting min words |
| `image` | photograph of handwritten working, a pasted screenshot, a scanned diagram | at least one image attached + short caption meeting min words |
| `mixed` | working + explanation together, or drawing/image + explanation | every declared part passes its own rule |

**Per-box attributes:** `data-type` · `data-min` (min words, prose/caption) · `data-kw` (min key terms) · `data-answer` (pipe-separated accepted answers) · `data-tol` (tolerance, absolute or 5%) · `data-units` · `data-sf` (significant figures) · `data-must` (required tokens for code/chem) · `data-lang` · `data-dok` and `data-max` on Main Task boxes · `data-hint` (see Guided Practice) · `data-canvas` (blank | grid | axes | lined | dotted background for draw) · `data-labels` (comma-separated labels the drawing must include, shown as a tick list) · `data-images` (max number of attachments, default 2) · **`data-qid`** (stable question id, sent to LISM in every event — required on every box).

---

## 2. VALIDATION RULES BY TYPE

**Universal:** blank is always rejected. Each box has a live meter showing what is still required (words, key terms, units, ticked items) and, on Submit, gives a specific reason for rejection — never a generic "wrong".

- **prose** — reject if below `data-min` words, below `data-kw` key-term matches, or gibberish (repeated character runs of 4+, a majority of tokens with no vowel, no recognisable word tokens). Apply the vowel-based gibberish test only to Latin-script prose.
- **numeric** — parse robustly: strip spaces, thousand separators, currency symbols and trailing units; treat 1/2, 0.5, 50%, 2^3, 2e3, −, and Arabic-Indic digits ٠١٢٣٤٥٦٧٨٩ as equivalents. Compare to `data-answer` within `data-tol` (default 1%, exact for integers). If `data-units` is set, a right number with missing or wrong units is partial, not full. If `data-sf` is set, check significant figures and say so. Never judge a numeric answer by word count.
- **symbolic** — normalise before comparing: strip whitespace, `*`→×, `sqrt(x)`→√x, `pi`→π, `<=`→≤, `>=`→≥, `!=`→≠, handle `^` powers, remove redundant outer brackets, and sort additive terms so 2y+3x equals 3x+2y. Hold several accepted forms in `data-answer` (e.g. `y=2x+3|y=3+2x`). Where full equivalence can't be checked reliably, report "form accepted — teacher to verify" rather than claiming certainty.
- **chem** — element symbols are case-sensitive (Co ≠ CO); accept H2O, H₂O, H_2O; accept state symbols (s) (l) (g) (aq); accept `->`, →, ⇌, `=` as arrows. For balancing, parse both sides, count atoms per element and check charge, then report which element is unbalanced. Never gibberish-test formulae.
- **code** — check the structures in `data-must` (e.g. `class,def,__init__,self,return`), indentation presence and a runnable-looking statement; ignore word count and never gibberish-test code. Report which required element is missing.
- **short** — normalise case, trim, collapse spaces, strip accents/diacritics for Latin languages (élève = eleve), match against `data-answer` synonyms. One-word answers are valid.
- **checklist** — tick boxes plus one short justification; accepted when the required number are ticked and the justification meets `data-min`. Use for PE, Art, Design, drama, music, or any lesson whose real output is a performance or artefact.
- **draw** — accepted when the canvas contains real marks (compare against a blank canvas, and require a minimum number of drawn strokes or ink pixels so a single accidental dot is rejected), the student has ticked every required label in `data-labels`, and the caption meets `data-min` words. The drawing itself cannot be auto-marked — report "Diagram submitted — teacher marks the diagram" and award the caption/label part of the rubric only, leaving the diagram marks to the teacher override.
- **image** — accepted when at least one image is attached and the caption meets `data-min` words. Never claim to judge image content; report "Image submitted — teacher marks the work."
- **mixed** — every declared part must pass, and feedback must say which part failed.

Every acceptance must also emit `student_submitted` (Section 0b) with that box's `data-qid`, its stage id, the mark awarded and the keywords detected.

---

## 2b. CODE, FORMULA, DRAWING AND IMAGE ANSWERS

**Code entry (`code`, when `PROFILE.code`)** — the box must behave like a small code editor, not a paragraph field:

- Monospace font, `white-space:pre`, spellcheck off, autocorrect/autocapitalise off, wrap off with horizontal scroll.
- Tab inserts spaces (2 or 4, stated on screen) instead of moving focus; Shift+Tab outdents. Provide a visible note that Esc then Tab moves focus onward, so keyboard users are never trapped.
- Auto-indent: Enter keeps the current line's leading whitespace, and increases it after a line ending in `:` (Python) or `{` (C-family/JS).
- Optional line numbers in a gutter that stays aligned when scrolling, and a language label (e.g. "Python 3").
- Indentation is preserved exactly in the accepted answer, the download and the print — never collapse or trim whitespace, because in Python indentation is the answer.
- Never execute code. Validation is structural only (`data-must` tokens, indentation present, balanced brackets and quotes), plus an optional style note ("no `self` in your method parameters").
- Model answers for code appear as a formatted code block with a "Copy" button, once unlocked.

**Formula entry (`numeric`, `symbolic`, `chem`)** — as specified in Section 4, plus:

- A live preview line beneath the box rendering what the student typed (3/4 → ¾, x^2 → x², H2O → H₂O, sqrt(9) → √9), so they can see their expression the way the teacher will read it.
- The symbol palette must be reachable by keyboard (buttons, not divs) and must not steal focus from the box.
- Fraction and index helpers: a button that inserts a fraction template with the caret in the numerator, and superscript/subscript toggles.

**Drawing (`draw`, when `PROFILE.draw`)** — an inline sketch pad, all client-side:

- A `<canvas>` with a chosen background from `data-canvas` — plain, squared grid, labelled x/y axes, ruled lines or dotted paper — sized responsively but with a fixed internal resolution so drawings stay sharp, and scaled for high-DPI screens.
- Tools: pen with 3 thicknesses, 4–6 colours, eraser, straight-line tool, text label tool (tap to place a short label), undo, redo, and Clear (with confirmation).
- Pointer events so it works with a mouse, a finger and a stylus on a tablet or smart board; disable page scrolling while drawing inside the canvas (`touch-action:none`) and re-enable outside it.
- A required-labels tick list from `data-labels` beside the canvas (e.g. "nucleus, cell membrane, cytoplasm") that the student ticks off, plus a caption box explaining the diagram.
- The drawing is stored as a PNG data URL and appears in the download file, the completed printout and the summary. Include an "Insert the printed diagram frame instead" behaviour for the blank paper copy — print an empty bordered box with the chosen background so students can draw by hand.

**Images (`image` and optional attachments on any box, when `PROFILE.images`)** — three ways in, all client-side, nothing uploaded anywhere:

- **Paste** — listen for `paste` and accept an image from the clipboard (a screenshot of code output, a graph from GeoGebra, a photo).
- **Choose file / drag and drop** — a file input accepting `image/*`, plus a drop zone with a visible hover state.
- **Camera** — on tablets and phones use `capture="environment"` so a student can photograph handwritten working or a completed practical.
- Show a thumbnail with the filename, a Remove button, and a limit from `data-images` (default 2). Downscale anything wider than ~1600px and re-encode to JPEG/WebP so the downloaded file stays a sensible size; reject non-image files and files over a stated limit with a clear message.
- Attachments are included in the download file and the completed printout, and are listed in the completion summary ("2 images attached").
- State plainly on the worksheet that images stay on the student's own device — they are never uploaded, and LISM receives only the fact that an attachment exists, never the image itself.

Because drawings and images cannot be auto-marked, any DOK question using them must have its diagram/image marks awarded by the teacher override, with the auto-estimate covering only the caption, labels and written reasoning — and the on-screen wording must make that split obvious.

---

## 3. LANGUAGE, SCRIPT AND RTL HANDLING

Set `<html lang>` and `dir` from PROFILE. When `dir:'rtl'`, mirror the whole worksheet — sticky header, section numbering, progress bar, DOK badges, tables and objective colour bars — but keep code blocks, formulae and numbers in `dir:'ltr'` islands so they don't reverse. Tab order must follow reading order.

Script-aware word counting: Arabic ؀-ۿ, Urdu, Hindi ऀ-ॿ, and Chinese/Japanese (characters ÷ 2 as an approximate word equivalent). Do not rely on Latin-only regex.

Arabic normalisation before comparison: strip tashkeel ً-ْ, remove tatweel ـ, unify alef أ إ آ ٱ → ا, ى → ي, ة → ه, unify hamza forms, convert Arabic-Indic digits to Western.

French/Spanish/Urdu: accent-insensitive comparison for short answers, correct accents kept in model answers.

Keywords and objectives appear in the language of instruction; for bilingual classes show term + translation in the same chip.

Never apply the English vowel gibberish test to non-Latin script — detect only repeated-character runs and single-character spam there.

---

## 4. MATH AND FORMULA RENDERING (offline-safe)

- **Primary:** write all display maths as inline MathML or Unicode (x², √, ≤, π, ∫, Σ, θ, °, ½, →) using `<sup>`/`<sub>` and CSS fraction spans — zero dependencies, renders everywhere.
- **Optional upgrade:** if `PROFILE.math`, attempt MathJax from CDN purely as progressive enhancement, wrapped so failure is silent and the MathML fallback stays visible. Never show raw `$...$` or a blank gap offline.
- **Symbol palette:** on every numeric, symbolic and mixed box in a maths or science worksheet, show a small insert-at-cursor row — √ x² x³ ^ π ≤ ≥ ≠ × ÷ ± ° θ Δ Σ ∫ ( ) / fraction (plus → ⇌ (s) (l) (g) (aq) when `PROFILE.chem`). Clicking inserts at the caret and keeps focus. Also accept typed ASCII equivalents (sqrt, ^2, pi, <=, ->) so a plain keyboard never blocks a student.
- Every maths question gets a large working-out box (method) plus a separate single-line final answer box, marked separately.

---

## 5. WORKSHEET LAYOUT, NAVIGATION AND NO-OVERLAP RULES

This is a scrolling document, not a deck. Enforce all of the following:

- One vertical column, max width ~1100px, centred, generous white space; each section is a numbered card with a coloured left border and a clear heading (e.g. "Section 3 · Starter · Recommended Duration: 5 minutes · 2 marks") carrying `data-stage="<manifest id>"`.
- Sticky header at the top holding the worksheet title, the keyword strip, the shortened ALL/MOST/SOME objectives, a live progress bar (sections completed / total), the running mark out of 10, and a collapse toggle. It must be slim (two compact rows maximum), must collapse to a single row on scroll or on demand, and must never cover section content — offset the content by the header's measured height in JS, recalculated on load, on resize and on collapse. Do not hard-code the offset. The header shows the current section's recommended duration as text, never a countdown.
- A section jump menu (a row of numbered chips or a slim side rail) that scrolls smoothly to any section, with completed sections ticked green and the current one highlighted. Use `scroll-margin-top` equal to the sticky header height so a jumped-to heading is never hidden underneath it.
- Nothing overlaps: only the header (and optional side rail) may be sticky; everything else is normal flow. Text wraps and is never clipped; no fixed heights on text containers; long formulae, tables and code scroll inside their own box rather than widening the page.
- `clamp()` font sizes; single column below 900px; touch targets at least 44px so it works on a tablet; text inputs must not trigger zoom on iOS (16px minimum font size).
- Keyboard-friendly: Tab moves through boxes in reading order, Ctrl/Cmd+Enter submits the focused box, and no keyboard shortcut hijacks normal typing.
- **Inside LISM the worksheet sits in an iframe** — it must fill its frame at any size, and its own sticky header must not fight LISM's chrome. Never assume the full viewport.
- **Print/PDF stylesheet (`@media print`)** — A4 portrait, page-break-inside avoided within a section, sticky header printed once as a plain masthead, jump menu and buttons hidden, all collapsed content expanded except model answers, and typed answers printed as they are — code with its indentation intact in a bordered monospace block, canvas drawings printed as images, attachments printed at a sensible size, none of them cut across a page break. Include two buttons: **Print my completed worksheet** and **Print blank copy** (the second replaces every input with ruled writing lines, every code box with a bordered monospace grid and every drawing canvas with an empty framed box on the chosen background, so the teacher can hand out paper copies).

---

## 6. PERSISTENT REFERENCE PANEL

The keyword strip and the three differentiated objectives — ALL (green), MOST (yellow), SOME (blue) — must be visible or one tap away at all times: in the sticky header when collapsed, and repeated in full inside Section 2. Colour must never be the only signal — always pair the colour with the word ALL / MOST / SOME. In maths and science worksheets the strip may include a key formula chip; in language worksheets show term + translation.

---

## 7. MODEL ANSWERS AND HINTS — LOCKED UNTIL THE STUDENT RESPONDS

Every model answer sits inside a collapsible toggle that starts locked and unopenable. While locked it reads "🔒 Submit your answer first to unlock the model answer" and clicking does nothing — it must not open, even briefly.

- A section's toggle unlocks only when that section's boxes have been accepted (all items in the Exit Ticket; all four DOK questions of the student's chosen pathway before the Main Task model answers unlock — see Section 7b).
- Once unlocked it reads "Reveal model answer" and stays closed by default.
- Include a small teacher override ("Teacher: unlock all answers") for whole-class feedback, and keep model answers out of the student print unless the teacher override is active. In preview mode (Section 0e) every model answer is freely openable.
- **Hints are different from answers:** `data-hint` gives up to two staged hints per Guided Practice and Main Task item. A hint gives the next step or the formula to use, never the answer, and using a hint is logged and shown in the summary ("2 hints used") **without reducing the mark**. Report the count in `activity_completed`.

---

## 7b. STUDENT PATHWAY CHOICE, EXTENSIONS AND MARK VISIBILITY

The student always chooses their level. Generate the Main Task three times over — a full ALL, MOST and SOME pathway, each with its own DOK 1 (2 marks), DOK 2 (3 marks), DOK 3 (3 marks) and DOK 4 (2 marks) questions on the same topic against the same 10-mark rubric, but at different levels of demand and scaffolding:

- **ALL (green)** — more scaffolding: sentence starters, partially completed frames, given values or code skeletons, one step at a time.
- **MOST (yellow)** — standard grade-level demand with minimal scaffolding.
- **SOME (blue)** — greater demand: less given, multi-step reasoning, comparison, justification or an unfamiliar context.

**Every pathway is graded out of the full 10 marks. This is non-negotiable:**

- A student who chooses ALL is marked against the same rubric, with the same weightings (DOK 1 = 2, DOK 2 = 3, DOK 3 = 3, DOK 4 = 2), and can earn a genuine 10 / 10. There is no cap, no scaling down, no deduction and no asterisk for choosing ALL — the pathway changes the demand of the questions, never the marks available.
- The mark display must never imply otherwise: show "Main Task: 8 / 10 (ALL pathway)", never "8 / 10 — reduced level" or a percentage of a smaller total.
- The same applies to MOST and SOME: all three are out of 10 with identical criteria weightings, so the only difference between pathways is the difficulty of the questions.
- The rubric descriptors are applied to the demand of the chosen pathway — "Correct, uses key terms" means correct for the questions that student was actually answering.

**Extensions carry no marks at all** — they are recognised with a certificate. There is no bonus score, no points and no leaderboard:

- The Main Task total stays exactly 10, whichever pathway was chosen and whether or not any extension was attempted.
- When an extension is submitted, validate it like any other box (word count, key terms, units, structure) and confirm it as completed. Do not score it, do not show a mark out of anything, and never display an unattempted extension as 0 — show "not attempted".
- Completed extensions unlock an Extension Achievement Certificate (Section 7c) carrying content-specific feedback about what that student actually did.
- The completion summary, the printout and the downloaded answer file list the graded 10, the pathway chosen and the extensions completed — as achievements, not as marks.

**Rules for the chooser:**

- At the top of the Main Task show three large selectable cards — ALL / MOST / SOME — each labelled with its colour and its word plus a one-line description of what that pathway asks for. Nothing is graded until a pathway is chosen, and the choice appears in the sticky header, the completion summary, the printout and the downloaded answer file. Report it to LISM in `activity_completed`.
- Only the chosen pathway's four questions are visible; the other two stay hidden but reachable at any time through a "Change level" control. Switching level must never delete work already typed, drawn or attached — keep everything, and state clearly which pathway the current /10 refers to.
- Any student may choose any pathway and may move up or down at any point. Never lock a student out of a level, never label a pathway "low" or "high", and never auto-assign a level for them.

**Extension tasks per DOK.** Every DOK question has its own optional extension, labelled "Extension — DOK 1/2/3/4", which unlocks as soon as that DOK question is submitted and accepted — so a student who finishes early always has somewhere to go without waiting for the class. Extensions raise demand within the same DOK strand (a harder case, an edge case, a justification, an alternative method). They carry no marks — completing one earns the Extension Achievement Certificate described in Section 7c, and they are never required.

Because there are no timers, nothing unlocks or locks on the clock — extensions unlock on completion of their own question, and the model answers unlock on completion of the whole Main Task.

Once all four questions in a pathway are accepted, show a quiet "Try the level above" option that reveals the higher pathway's questions as extra practice, marked separately, leaving the graded /10 untouched unless the student explicitly asks to be graded on the higher pathway instead.

**Model answers stay locked until the whole Main Task is finished.** All four DOK questions of the chosen pathway must be submitted and accepted before the Main Task model answers can open; extensions and "level above" practice never count towards this. A part-finished Main Task keeps every toggle sealed and shows "🔒 Complete all four questions to unlock the model answers (3 of 4 done)".

**The student always sees their own marks against the rubric out of 10.** After each accepted response show, beside that question, the rubric level (0–3), the exact descriptor matched (e.g. "Mostly correct") and the marks earned out of that DOK's maximum. In addition:

- A persistent "My mark: x / 10" chip in the sticky header, updating live and showing how many criteria are still unmarked.
- Section 7 shows the full graded table — every criterion with its maximum, the level awarded, the descriptor matched, the marks earned, the running total out of 10 and the percentage — with the chosen pathway named above the table and any completed extensions listed beneath it as achievements, not marks.
- Marks are labelled "estimated — your teacher's mark is final", with a teacher override per criterion that recalculates the total instantly, and diagram/image marks shown as "awaiting teacher mark".
- Feedback must always say how to gain the missing mark ("You explained the method; add the units to reach 3/3"), never only the score.
- The graded rubric, the pathway and any completed extensions are included in the downloaded answer file and the completed printout.

---

## 7c. EXTENSION ACHIEVEMENT CERTIFICATE (PDF)

Completing an extension earns recognition, not points. Build an Extension Achievement Certificate that the student can save as a PDF, and make the feedback on it specific to what that student actually did.

**When it becomes available**

- The "Create my certificate" button appears only once at least one extension has been submitted and accepted, and only after all four graded questions of the chosen pathway are complete. It is greyed out with the reason shown until then.
- The student's name is required; if the name field is empty, prompt for it before generating (a certificate with a blank name is never produced).
- Include a teacher approval toggle ("Teacher: approve certificate") plus a one-line teacher comment field, so the certificate is issued by the teacher rather than self-awarded. State on screen whether approval is required in this class.
- Only extensions genuinely completed are named. Never list an extension that was skipped, and never award the certificate for the graded task alone.

**What goes on it**

- A heading — "Certificate of Achievement · Extension Challenge" — with an editable school or class name field.
- Student name, class, subject, grade, week, [TOPIC NAME] and the date.
- The extension(s) completed, named with their DOK strand, e.g. "Extension — DOK 3: Application" and "Extension — DOK 4: Evaluation".
- Content-specific commendation of 2–3 sentences, assembled from real signals in that student's work — which extension(s) they completed, which lesson keywords they used correctly, the rubric levels they reached, and whether their answer included code, a calculation, a balanced equation, a diagram or an evaluation. Write these as topic-specific statements, e.g. "Aisha extended her work on classes in Python by designing a Loan class that connects books to members, and justified her structure using the terms encapsulation, method and instance accurately." Generate a small bank of such statements keyed to the topic and to each DOK strand, and select from it based on what was actually detected.
- Never fabricate. No praise for work not submitted, no invented scores, no claims about quality the file cannot verify. If a student completed only part of an extension, the wording says so plainly ("recognised for extending DOK 2: Skill").
- A forward-looking line — one sentence naming what to try next in this topic, so the certificate teaches as well as rewards.
- Teacher signature line and date, with space for the handwritten signature on the printed copy.
- No marks anywhere on the certificate — this replaces bonus scoring entirely.

**How the PDF is produced (offline-safe, no dependencies)**

- Render the certificate as an on-screen A4 landscape panel with a decorative border, the lesson's colour scheme and large readable type, so the student sees exactly what they will get.
- Primary export: a "Save as PDF" button that calls `window.print()` with a print stylesheet scoped to the certificate only — `@page { size: A4 landscape; margin: 0 }`, every other element `display:none`, no page breaks inside the certificate, and colours preserved with `print-color-adjust:exact`. The browser's own "Save as PDF" destination produces the file, so nothing needs to be installed and it works offline.
- Secondary export: a "Download as image" button that draws the certificate to a canvas and saves a PNG, for students whose browser print dialogue is restricted.
- Optional progressive enhancement: if a PDF library is reachable from a CDN, offer a direct one-click PDF download — but the print route must remain fully functional when offline, and the file must never depend on the library loading.
- The certificate follows `PROFILE.lang` and `PROFILE.dir`, so an Arabic lesson produces a fully right-to-left certificate with the commendation written in Arabic.
- Certificates are generated entirely on the student's own device; nothing is uploaded.

---

## 8. WORKSHEET STRUCTURE (exactly 10 sections)

Each section card carries `data-stage="<manifest id>"` and emits `stage_viewed` when it becomes the current section.

**Section 1 — HEADER** (`header`): [TOPIC NAME], subject, grade, week; fields for Student name, Class and Date (these appear on the printout and in the downloaded answer file); a one-line "How to use this worksheet" instruction; and the time guide for the 50 minutes.

**Section 2 — KEYWORDS & OBJECTIVE** (`keywords`, Recommended Duration: 2 minutes): keywords as a prominent vocabulary strip with a one-line definition revealed on click; the full lesson objective in one sentence; the full ALL / MOST / SOME success criteria in student-friendly "I can…" language, colour coded green / yellow / blue, with a line telling students they will choose which level to attempt in the Main Task and may change it at any time.

**Section 3 — STARTER / RETRIEVAL** (`starter`, Recommended Duration: 5 minutes + feedback): one open-ended review question about [PREVIOUS LESSON TOPIC] plus two quick recall items of the profile-appropriate type. Instruction: "Your answer must use at least 1 key term from this lesson." Note: "Feedback: teacher reviews responses and students may explain their answers." Model answer in the locked toggle.

**Section 4 — KNOWLEDGE BOX / WORKED EXAMPLE (I DO)** (`knowledge-box`, Recommended Duration: 10 minutes for Sections 4 and 5 together): the topic explained in 3 clear parts with one labelled diagram or simple interactive visual, and one fully worked example presented as a step-through (each step revealed by clicking "Next step", with the reasoning stated for each step). Minimal text, visuals dominant. **This section is the student's reference while they work — it must stay available, not disappear**, even when LISM has moved the class on to a later stage.

**Section 5 — GUIDED PRACTICE (WE DO)** (`guided-practice`): 2–3 scaffolded items rising in difficulty, each with a partially completed frame or sentence starter, a staged hint button (`data-hint`), and instant validation. Not marked towards the 10 — this is practice, and feedback should coach ("You have the right method; check your units"). Emit `student_submitted` with `mark: null` so the teacher can see engagement without it affecting the graded total.

**Section 6 — MAIN TASK** (`main-task`, Recommended Duration: 10 minutes + feedback, 10 marks): the student first chooses their pathway — ALL, MOST or SOME — then works through that pathway's DOK 1 Recall (2 marks), DOK 2 Skill (3 marks), DOK 3 Application (3 marks) and DOK 4 Evaluation (2 marks) questions, each with a coloured DOK badge (DOK1 green, DOK2 blue, DOK3 amber, DOK4 red) and its own optional extension that unlocks on submission. Generate all three pathways in full, as specified in Section 7b. Choose answer types per question — typically short/numeric for DOK 1, numeric/symbolic/code/draw/mixed for DOK 2, mixed for DOK 3, prose for DOK 4 — and where the subject's real answer is a diagram, a graph, a circuit, a map or handwritten working, use `draw` or `image` (or `mixed` with a written explanation beside it) rather than forcing the student to describe it in words. Instruction: "Answers must include at least 2 key terms" for prose parts; for numeric or symbolic parts require correct method and units instead, and say so on screen. Note: "Feedback: teacher gives feedback on responses and students may defend their work."

**Section 7 — MARK SCHEME & FEEDBACK** (`mark-scheme`): the rubric table, the student's live marks, and the teacher override. See Section 9 below for the marking behaviour, which is mandatory.

**Section 8 — CONNECTION LINK** (`connection`, Recommended Duration: 3 minutes) — TEACHER'S/STUDENT'S CHOICE: three tabs — "UAE Link", "AI Link", "Cross-Curricular Link"; clicking one reveals that version and hides the others. Generate all three: (1) UAE Link — one sentence connecting the topic to life, industry or culture in the UAE; (2) AI Link — one sentence on how AI or emerging technology relates to or is transforming this topic; (3) Cross-Curricular Link — one sentence connecting the topic to another school subject. Each has a short response box and a 3-option poll that tallies live when clicked. Warm gold or green accent so the section stands out.

**Section 9 — EXIT TICKET** (`exit-ticket`, Recommended Duration: 5 minutes + feedback): 5 short items testing this lesson's objectives — fill-in-the-blank for terminology subjects, or 5 quick numeric/symbolic/chem items for maths and science — each with its own validated box and its own `data-qid`. Instruction: "Use at least 1 key term per answer" (or "Show units in every answer" for numeric lessons). Note: "Feedback: teacher reviews exit responses and students may explain their thinking." Model answers in the locked toggle, unlocking after all 5 are submitted.

**Section 10 — REFLECTION, SELF-ASSESSMENT & SUBMIT** (`reflection`, Recommended Duration: 5 minutes): 3-2-1 boxes (3 things you learned, 2 to explore further, 1 you are unsure about) with minimum word counts; a self-assessment where the student ticks which of ALL / MOST / SOME they have met and justifies it in one sentence; one optional extension challenge aimed at SOME (recognised by certificate, outside the 10); and the completion report and submit controls (Section 10 below).

---

## 9. MARKING, FEEDBACK AND THE RUBRIC (mandatory behaviour)

The moment a Main Task response is accepted, mark it against the rubric and show, next to that question: the rubric level awarded (0–3), the descriptor matched (e.g. "Mostly correct") and the marks earned out of that DOK's maximum. Mirror every mark into a "Your mark" column in the Section 7 rubric table, update a running total out of 10 live in both the rubric header and the sticky header, and flag which criteria are still unmarked. **Emit `student_submitted` at the same moment**, carrying `dok`, `rubricLevel`, `mark`, `maxMark` and `keywordsUsed`, so the teacher's dashboard shows the same picture the student sees.

Marking basis depends on answer type: correctness against the answer key for numeric, symbolic, chem, short and code (full marks = correct with valid method, units and structure; partial = right method wrong value, or right value with wrong units or significant figures; low = attempt only); depth, key-term coverage and reasoning for prose and the prose half of mixed; ticked criteria plus justification for checklist; for draw and image, mark only the labels, caption and reasoning automatically and hold the diagram or attachment marks for the teacher override, showing "awaiting teacher mark" rather than a guessed score. Label the total "estimated — teacher's mark is final" and give the teacher a 0/1/2/3 override selector per DOK that recalculates the total instantly.

Feedback wording must be specific and actionable ("Right value, but the unit is missing — add m/s²"), never just "incorrect".

**MAIN TASK MARKING RUBRIC (10 marks total):** DOK 1 Knowledge/Recall — 3: Correct, uses key terms, 2: Mostly correct, 1: Partial, 0: Blank or gibberish — /2. DOK 2 Skill/Accuracy — 3: Fully correct and explained, 2: Mostly correct, 1: Partial and weak, 0: Blank or gibberish — /3. DOK 3 Application — 3: Clear reasoning, 2: Mostly applied, 1: Partial, 0: Blank or gibberish — /3. DOK 4 Evaluation — 3: Well-justified, 2: Reasonable, 1: Limited, 0: Blank or gibberish — /2. TOTAL — /10.

---

## 10. SAVING, SUBMITTING AND THE STUDENT COMPLETION REPORT

**Completion report in Section 10** — built only from what actually happened, never invented, never padded:

- **Completion status** and sections completed out of 10.
- **Estimated Main Task score out of 10**, broken down per DOK, with the pathway named ("8 / 10 · MOST pathway"), labelled *estimated — your teacher's mark is final*.
- **Participation summary:** responses submitted, hints used, extensions completed, items correct first time (numeric subjects), diagrams drawn, images attached, poll answered.
- **Keywords used:** which of the lesson's keywords the student actually used, as ticked chips, and which they did not.
- **Time spent** — taken from LISM's `time_update` command. The worksheet has no timer of its own, so standalone or where LISM has not sent one, **omit this line entirely rather than inventing a number**. (The download file's completion timestamp is separate and still permitted.)
- **Teacher review pending** — anything awaiting a human mark (diagrams, attachments, criteria under teacher override), worded "Your teacher will review and confirm your final mark."
- The self-assessed ALL/MOST/SOME level.

Emit `activity_completed` with the same figures at the moment the report is first shown.

**Download my answers** — a button that builds a self-contained HTML file client-side with a Blob and downloads it, containing the student's name, class, date, every question with the student's answer, each mark awarded, the total and the timestamp. Code answers keep their exact indentation inside `<pre>`; drawings are embedded as inline PNG data URLs; attached images are embedded the same way, so the single file opens complete with no missing links. Offer a plain-text version as a second option for students whose email blocks HTML, noting that the text version cannot carry the diagrams.

**Print my completed worksheet** and **Print blank copy** as described in the layout rules.

**Draft protection:** attempt a lightweight autosave of typed answers, canvas drawings and attachments so an accidental refresh does not lose work, wrapped in try/catch so the worksheet still works perfectly if storage is unavailable, blocked or full (images are large — if saving fails, keep the typed answers and warn that attachments are not saved). Show a small "Draft saved" note and a "Clear my work" button that asks for confirmation. Never make any feature depend on storage succeeding.

**What leaves the device.** Say this accurately on the worksheet, and scope it to the context:

- **Standalone (opened outside LISM):** nothing is sent anywhere — every answer, drawing and attachment stays on the student's own device.
- **Inside LISM:** answers, marks and progress are reported to the teacher's live dashboard so the teacher can see and mark the work. Drawings and photographs are **not** uploaded — LISM is told only that an attachment exists. Word the on-screen note plainly, e.g. "Your teacher can see your answers and marks in this lesson. Your photos and drawings stay on this device."

Never print the blanket claim "nothing is ever sent anywhere" when the worksheet is running inside LISM — it would be untrue.

---

## 11. DESIGN RULES

One consistent colour scheme; numbered section cards with coloured left borders; DOK badges colour coded (DOK1 green, DOK2 blue, DOK3 amber, DOK4 red) and always paired with the number; ALL/MOST/SOME always paired with their word; large readable fonts with generous line spacing suitable for reading on a tablet and on paper; the recommended duration shown beside every section title and **no timer or countdown of any kind**; model answers only inside locked collapsible toggles; smooth scrolling and gentle reveal animations only — no animation that delays reading; strong colour contrast; no overlapping elements at any width; clean A4 print output.

---

## 12. TIMING (metadata and guidance only)

50-minute period — Keywords & Objectives 2 minutes, Starter 5 minutes, Knowledge Box + Guided Practice 10 minutes, Main Task 10 minutes, Connection Link 3 minutes, Exit Ticket 5 minutes, Reflection 5 minutes, plus 10 minutes reserved across the Starter, Main Task and Exit Ticket for teacher feedback and for students to explain or defend their work.

These figures appear in two places and nowhere else: as `durationSeconds` in the manifest (so LISM's dashboard can show and use them), and printed beside each section title as guidance. They are never counted down inside the worksheet, never enforced, and never used to lock anything. In homework mode show the total expected time in the header and keep the per-section guidance.

---

## 13. SELF-CHECK BEFORE YOU FINISH

State briefly that you have verified:

**LISM integration** — exactly one valid `lism-manifest` JSON block with 10 stages whose ids match every section's `data-stage` and every event's `stageId`; `activity_ready` emitted on load inside LISM; `start_stage`, `stage_ended`, `pause`, `resume`, `lock`, `unlock`, `set_config` and `time_update` all handled, unknown commands ignored silently; **`student_submitted` emitted on every accepted answer** with `data-qid`, stage id, mark, DOK and keywords — the worksheet reports to the teacher dashboard rather than keeping marks to itself; Guided Practice submissions carry `mark: null`; `start_stage` highlights the current section without hiding the Knowledge Box; `?preview=1` gives Previous/Next plus a section counter, unlocks every section, and emits nothing at all; the worksheet opens standalone in a browser and works fully offline with no LISM present; the "what leaves the device" wording is accurate in both contexts and never claims "nothing is ever sent anywhere" while inside LISM.

**Pacing** — no timers, countdowns or time-based pacing logic anywhere in the file; only recommended durations as manifest metadata and as text beside section titles; pause and resume preserve every typed, drawn and attached answer and restore scroll position.

**Teacher settings** — copy-paste protection off by default and applied only to answer boxes when enabled, leaving question text and the Knowledge Box selectable; focus monitoring off by default, one warning per physical departure, maximum 3, and the worksheet never locks on its own authority.

**Educational framework** — exactly 10 sections; the sticky header never covers content and jump links land correctly at any width; nothing overlaps at 1366×768, on a 390px-wide phone, or inside the LISM iframe; all three ALL/MOST/SOME pathways generated in full with a working chooser that preserves typed, drawn and attached work when switching; every pathway including ALL graded out of the full 10 with no cap or scaling; a per-DOK extension that unlocks on submission, carries no marks, and produces a content-specific achievement certificate that saves as an A4 landscape PDF offline; Main Task model answers sealed until all four graded questions are accepted; the student's marks against the rubric visible out of 10 at all times; every model-answer toggle locked until submission, with hints separate from answers and never reducing the mark; each DOK marked on submit with a live total out of 10 and a working teacher override; every answer box validated by its declared type with a specific, actionable rejection reason; code boxes take Tab as indentation without trapping focus and preserve whitespace everywhere; the formula preview renders what was typed; the sketch pad works with mouse, finger and stylus without scrolling the page, and undo/clear behave; paste, file-choose, drag-drop and camera capture all attach an image, with limits enforced; download, print-completed and print-blank all produce correct output including code indentation, drawings and attachments; the completion report shows only real figures and omits time spent when LISM has not provided it; math/chem/code/draw/image/RTL features present and working offline as required by the subject profile.
