# Master Prompt — Interactive HTML Lesson Deck (v9, all subjects)

**LISM-integrated · teacher-controlled pacing · pathway choice graded out of 10 · extension certificate instead of bonus marks**

> **What changed from v8** — the educational framework is unchanged. v9 makes the deck a first-class LISM AI Classroom activity: it emits a lesson manifest, reports every response to the teacher's live dashboard, hands pacing (start/pause/resume/end) to the teacher, adds a teacher preview mode, a student completion report, optional copy-paste protection and optional focus monitoring. It still opens standalone in any browser and works fully offline.

Fill in the bracketed fields, then paste the whole prompt.

Fill in: `[TOPIC NAME]` · `[SUBJECT]` · `[GRADE]` · `[WEEK X]` · `[PREVIOUS LESSON TOPIC]` (Leave keywords blank and write "guess the keywords yourself" if you want them generated. Leave the SUBJECT PROFILE values blank and Claude will choose them from the subject.)

---

Build a single self-contained interactive HTML slide deck for **[TOPIC NAME]** — [SUBJECT], Grade [GRADE], Week [WEEK X]. Previous lesson: [PREVIOUS LESSON TOPIC]. Guess the 5–6 lesson keywords yourself from the topic.

One HTML file, no required external dependencies, no localStorage, runs by opening the file in any browser. It must work as a presentable deck: one slide visible at a time, full-screen friendly, Next and Previous buttons, left/right arrow key support, a slide counter (e.g. "3 / 10") and a progress dots indicator at the bottom. Students type and submit answers directly into the slides. Arrow keys must NOT change slide while a student is typing in an input. Total lesson 50 minutes, including 10 minutes reserved across the Starter, Main Activity and Exit Ticket for teacher feedback and for students to explain or defend their work.

The deck must run correctly in **two contexts**, with no separate build:

1. **Inside LISM AI Classroom** — embedded in an iframe, paced by the teacher, reporting live to the teacher dashboard (Sections 0 and 0b).
2. **Standalone** — opened directly from the file system or a link, self-paced, no reporting, fully offline.

---

## 0. PACING — THE TEACHER CONTROLS TIME, NOT THE FILE (mandatory)

The deck contains **no timing mechanism of its own**. Do not build:

- Automatic timers in any section.
- JavaScript that starts a timer on first keystroke, focus, submission or any other student interaction.
- Countdown displays, clock faces, progress rings or timer UI of any kind.
- Auto-locking, greying out or disabling of inputs because time has passed.
- Time-based transitions between slides or sections.
- Any logic that controls or enforces lesson pacing (no `setInterval`, `setTimeout` or `Date`-based gating **for pacing purposes** — `setTimeout` for a toast auto-hiding or an input debounce is fine).

Instead:

- Carry the recommended duration for every stage as **metadata in the manifest** (`durationSeconds`, Section 0b).
- Print the recommended duration beside each section title as instructional guidance, e.g. `Starter (Recommended Duration: 5 minutes)`.
- Inside LISM, the teacher controls **Start · Pause · Resume · End · Next stage**, and LISM shows students the one synchronised countdown. The deck simply obeys the commands it is sent.
- Standalone, the student self-paces with Next/Previous and sees the recommended durations as guidance.

Recommended durations to carry: Keywords & Objective 2 min · Starter 5 min · Main Teaching 10 min · Main Activity 10 min · Connection Link 3 min · Exit Ticket 5 min · Reflection 5 min.

Everything else in this framework — activities, validation rules, DOK structure, scoring, keyword detection, sequential unlocking of model answers, the UAE/AI/Cross-Curricular section, reflection and overall lesson design — stays exactly as specified.

---

## 0b. LISM CLASSROOM INTEGRATION (mandatory)

This is what makes the deck a live LISM activity instead of an isolated page. **A deck that validates answers internally but never reports them will display perfectly and show the teacher nothing.**

### Detecting LISM

```js
const IN_LISM = window.parent !== window;
```

When false, run standalone: show the first slide, self-paced, emit nothing. When true, hand pacing to LISM and report events. The deck must never require LISM to function.

### The lesson manifest (required)

Emit exactly one inert JSON block in `<head>`, alongside (not instead of) the `PROFILE` object. LISM parses this server-side at upload, without running the page:

```html
<script type="application/json" id="lism-manifest">
{
  "lessonType": "lesson-deck",
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
    { "id": "title",          "label": "Title",                "type": "title",         "durationSeconds": 60,  "sequentialLock": false, "marks": null },
    { "id": "keywords",       "label": "Keywords & Objective", "type": "keywords",      "durationSeconds": 120, "sequentialLock": false, "marks": null },
    { "id": "starter",        "label": "Starter",              "type": "starter",       "durationSeconds": 300, "sequentialLock": true,  "marks": null },
    { "id": "objectives",     "label": "Learning Objectives",  "type": "objectives",    "durationSeconds": 60,  "sequentialLock": false, "marks": null },
    { "id": "main-teaching",  "label": "Main Teaching",        "type": "teaching",      "durationSeconds": 600, "sequentialLock": true,  "marks": null },
    { "id": "main-activity",  "label": "Main Activity",        "type": "main-activity", "durationSeconds": 600, "sequentialLock": true,  "marks": 10 },
    { "id": "rubric",         "label": "Marking Rubric",       "type": "rubric",        "durationSeconds": 120, "sequentialLock": true,  "marks": null },
    { "id": "connection",     "label": "Connection Link",      "type": "connection",    "durationSeconds": 180, "sequentialLock": true,  "marks": null },
    { "id": "exit-ticket",    "label": "Exit Ticket",          "type": "exit-ticket",   "durationSeconds": 300, "sequentialLock": true,  "marks": null },
    { "id": "reflection",     "label": "Reflection",           "type": "reflection",    "durationSeconds": 300, "sequentialLock": true,  "marks": null }
  ]
}
</script>
```

Rules: **one stage per slide, in order, ten stages for ten slides.** Ids must be stable, lowercase-hyphenated and unique — every event references a `stages[].id`, so a typo silently detaches that slide from the dashboard. `durationSeconds` is the recommended duration only. `marks` is 10 on `main-activity` and `null` elsewhere. Keep `deliveryMode` (the deck's own wording axis) and `sessionType` (LISM's enforcement axis) as two separate fields — never merge them. Give every slide a `data-stage="<id>"` attribute matching its manifest id.

### Commands LISM sends (parent → deck)

Listen on `window.addEventListener('message', …)` for `{ type: 'lism:command', command, … }`:

| `command` | Payload | The deck must |
|---|---|---|
| `start_stage` | `stage`, `stageIndex`, `serverTime` | Show only that slide; enable its inputs |
| `stage_ended` | — | Show "Waiting for your teacher…"; disable that slide's inputs |
| `pause` | — | Freeze interaction, show a paused notice, keep every typed answer |
| `resume` | — | Unfreeze and restore the previous view exactly |
| `lock` | `reason` | Disable every input and show the reason; not dismissible by the student |
| `unlock` | — | Re-enable inputs (the teacher cleared the lock) |
| `set_config` | `copyPasteProtection`, `focusMonitoring`, `maxWarnings` | Apply teacher settings (Sections 0c and 0d) |
| `time_update` | `elapsedSeconds`, `remainingSeconds` | Store for the completion report; do not render a countdown |

**Ignore unknown commands silently** — never throw, never break. This lets LISM add commands later without regenerating the deck.

### Events the deck sends (deck → parent)

`window.parent.postMessage({ type: 'lism:event', event, … }, '*')`:

| `event` | Payload | When |
|---|---|---|
| `activity_ready` | `stageCount` | Once on load, inside LISM only |
| `stage_viewed` | `stageId` | The visible slide changed |
| `response_update` | `stageId`, `questionId`, `charCount`, `wordCount` | Student is typing — **throttle to at most once per 2 s per box**; never send keystrokes or answer text |
| `student_submitted` | `stageId`, `questionId`, `correct`, `answer`, `mark`, `maxMark`, `dok`, `rubricLevel`, `keywordsUsed` | A box was submitted **and accepted** |
| `stage_completed` | `stageId`, `marksEarned`, `maxMarks` | Every required box on that slide is accepted |
| `activity_completed` | `pathway`, `totalMarks`, `maxMarks`, `stagesCompleted`, `keywordsUsed`, `extensionsCompleted` | Reflection slide reached with the lesson finished |
| `help_requested` | `stageId`, `questionId` | Student clicked "I need help" in the deck |
| `focus_warning` | `stageId`, `warningNumber`, `kind` | The deck's own focus monitor fired (Section 0d) |

**`student_submitted` is the one event the live dashboard cannot work without.** Emit it for every accepted answer — Starter box, each DOK question, each Exit Ticket blank, each Reflection box — with `stageId` exactly matching the manifest id of the slide it came from.

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
    case 'start_stage': showStage(d.stage.id); break;
    case 'stage_ended': showWaiting(); break;
    case 'pause':       setFrozen(true); break;
    case 'resume':      setFrozen(false); break;
    case 'lock':        applyLock(d.reason); break;
    case 'unlock':      clearLock(); break;
    case 'set_config':  Object.assign(LISM.config, d); applyConfig(); break;
    case 'time_update': LISM.elapsedSeconds = d.elapsedSeconds; break;
  }
});

if (IN_LISM) LISM.emit('activity_ready', { stageCount: STAGES.length });
else showStage(STAGES[0].id);
```

Because the deck is served from a different origin than the LISM page, `postMessage` is the only channel — never assume shared DOM, cookies or storage.

---

## 0c. COPY & PASTE PROTECTION (teacher-configurable)

Off by default. Enabled by `set_config { copyPasteProtection: true }`. When on, **inside answer inputs only**:

- Block `copy`, `cut`, `paste`, `contextmenu` and text drag-and-drop.
- Show a short, calm notice: "Copy and paste are switched off for this lesson — type your own answer."

Never disable keyboard navigation or browser accessibility features, and never block the whole page — only the answer boxes. Where the subject profile uses `image` answers, keep the image-paste path working (a photograph of handwritten working is not plagiarism) unless the teacher's setting explicitly covers attachments. Standalone, protection is off.

---

## 0d. FOCUS MONITORING (teacher-configurable)

LISM runs its own focus monitor on the student page and owns the authoritative count, the lock and the teacher notification. The deck's monitor is secondary and must not duplicate authority:

- Monitor only when `set_config { focusMonitoring: true }`.
- Watch tab switching (`visibilitychange`) and window blur/focus.
- Collapse one physical departure into **one** warning — `blur` and `visibilitychange` both fire for the same event, so a naive implementation double-counts.
- Emit `focus_warning` with an incrementing `warningNumber` and show the student a warning.
- Maximum 3 warnings (`maxWarnings`). **Do not lock on your own authority** — LISM sends `lock` when the limit is reached, so there is one source of truth. Show the lock state and disable inputs when that command arrives.

---

## 0e. TEACHER PREVIEW MODE

Teachers review a lesson before launching it, via `?preview=1` on the activity URL. When `preview` is true:

- Show **Previous / Next** controls and a stage counter ("4 / 10") so every slide can be inspected.
- Ignore `sequentialLock` entirely — every stage reachable in any order.
- **Emit no events whatsoever** and create no student data (the `LISM.emit` guard above handles this).
- Show a clear banner: "Preview — not a live lesson. Nothing is recorded."
- Model answers may be opened freely in preview, so the teacher can check them.

---

## 1. SUBJECT PROFILE (set this first — it drives all validation)

Before writing any HTML, choose and state a subject profile at the top of the file as a JS config object, then build every answer box to obey it. Infer sensible values from [SUBJECT] and [TOPIC NAME]:

```js
const PROFILE = {
  subject:'[SUBJECT]', grade:'[GRADE]', week:'[WEEK X]',
  lang:'en',            // 'en' | 'ar' | 'fr' | 'es' | 'ur' | 'hi' …
  dir:'ltr',            // 'rtl' for Arabic/Urdu — flips the whole layout
  math:false,           // true → math rendering + symbol palette
  chem:false,           // true → chemical formula & equation checking
  code:false,           // true → code editor behaviour + code-structure checking
  draw:false,           // true → sketch pad answer boxes enabled
  images:true,          // true → paste / upload / photograph an image into an answer
  defaultAnswerType:'prose'   // default box type for this subject
};
```

The values here must agree with the manifest's `subject`, `grade`, `week` and `topic`.

**Answer types** — every response box must declare one via `data-type`. Validation, feedback wording and rubric marking all switch on it:

| `data-type` | Use for | Accepted when |
|---|---|---|
| `prose` | explanations, evaluation, reflection | min word count + min key-term matches + not gibberish |
| `numeric` | maths, physics, chemistry calculations | value matches answer key within tolerance, correct units if required |
| `symbolic` | algebra, formulae, equations, expressions | normalised form matches any accepted form |
| `chem` | formulae and balanced equations | element-aware match, or atom counts balance on both sides |
| `code` | programming | required structures/tokens present, not prose length |
| `short` | fill-in-the-blank, single terms, dates | matches answer key or accepted synonyms (normalised) |
| `checklist` | PE, Art, Design, practical/performance work | required boxes ticked + short justification meeting min words |
| `draw` | diagrams, graphs, circuits, labelled sketches, maps | canvas is not blank + required label list ticked + caption meeting min words |
| `image` | photograph of handwritten working, pasted screenshot, scanned diagram | at least one image attached + caption meeting min words |
| `mixed` | working + explanation together, or drawing/image + explanation | every declared part passes its own rule |

**Per-box attributes:** `data-type` · `data-min` (min words, prose only) · `data-kw` (min key terms) · `data-answer` (pipe-separated accepted answers) · `data-tol` (numeric tolerance, absolute or 5%) · `data-units` (required unit string, e.g. m/s) · `data-sf` (significant figures required) · `data-must` (comma-separated tokens that must appear, code/chem) · `data-lang` (overrides profile language for this box) · `data-dok` and `data-max` on Main Activity boxes · `data-canvas` (blank | grid | axes | lined | dotted background for draw) · `data-labels` (labels the drawing must include, shown as a tick list) · `data-images` (max attachments, default 2) · **`data-qid`** (stable question id, sent to LISM in every event — required on every box).

---

## 2. VALIDATION RULES BY TYPE

**Universal:** blank is always rejected. Every box has a live meter showing what is still required (words, key terms, units, ticked items) and, on Submit, gives a specific reason for rejection — never a generic "wrong".

- **prose** — reject if below `data-min` words, below `data-kw` key-term matches, or gibberish. Gibberish test = repeated character runs (4+), a majority of tokens with no vowel, or no recognisable word tokens. Apply the vowel-based gibberish test only to Latin-script prose — see script handling below.
- **numeric** — parse the student's value robustly: strip spaces, commas as thousand separators, currency symbols, and trailing units; accept 1/2, 0.5, 50%, 2^3, 2e3, − (minus sign) and ٠١٢٣٤٥٦٧٨٩ Arabic-Indic digits as equivalents. Compare against `data-answer` within `data-tol` (default 1% or exact if the answer is an integer). If `data-units` is set, the unit must be present and correct — a right number with wrong or missing units scores partial, not full. If `data-sf` is set, check significant figures and say so in the feedback. Never judge a numeric answer by word count. Accept an empty-of-prose answer as complete.
- **symbolic** — normalise before comparing: strip all whitespace, lowercase (except where case is meaningful), convert `*`→×, `x`→× only when unambiguous, `^` to superscript form, `sqrt(x)`→√x, `pi`→π, `<=`→≤, `>=`→≥, `!=`→≠, remove redundant outer brackets, and treat 2y+3x as equal to 3x+2y for sums by sorting additive terms. Hold several accepted forms in `data-answer` (e.g. `y=2x+3|y=3+2x|2x+3=y`). Where full equivalence cannot be checked reliably, mark it as "form accepted — teacher to verify" rather than pretending certainty.
- **chem** — element symbols are case-sensitive (Co ≠ CO); accept subscripts written as H2O, H₂O or H_2O; accept state symbols (s) (l) (g) (aq); accept `->`, →, `=` as the reaction arrow and `+` between species. For balancing questions, parse both sides, count atoms per element and check they match, and check total charge — report which element is unbalanced. Never run the vowel gibberish test on formulae.
- **code** — check for required structures listed in `data-must` (e.g. `class,def,__init__,self,return`), correct nesting/indentation presence, and that a runnable-looking statement exists; ignore word count entirely and never gibberish-test code. Report which required element is missing.
- **short** — normalise case, trim, collapse spaces, strip diacritics/accents when `data-lang` is a Latin language (so élève = eleve), and match against `data-answer` synonyms. Accept one-word answers as valid.
- **checklist** — render the criteria as tick boxes plus one short justification box; accepted when the required number of boxes are ticked and the justification meets `data-min` words. Use this for PE, Art, Design, drama, music and any lesson whose real output is a performance or artefact rather than typed text.
- **draw** — accepted when the canvas contains real marks (compared against a blank canvas, with a minimum stroke or ink threshold so a stray dot is rejected), every required label in `data-labels` is ticked, and the caption meets `data-min` words. The diagram itself is not auto-marked — report "Diagram submitted — teacher marks the diagram" and leave those marks to the teacher override.
- **image** — accepted when at least one image is attached and the caption meets `data-min` words. Never claim to judge image content; report "Image submitted — teacher marks the work."
- **mixed** — every declared part must pass, and the feedback must say which part failed.

Every acceptance must also emit `student_submitted` (Section 0b) with that box's `data-qid`, its stage id, the mark awarded and the keywords detected.

---

## 2b. CODE, FORMULA, DRAWING AND IMAGE ANSWERS

**Code entry (`code`)** — the box behaves like a small editor: monospace, `white-space:pre`, spellcheck and autocapitalise off, no wrapping; Tab inserts 2 or 4 spaces rather than moving focus (Shift+Tab outdents, and a note explains that Esc then Tab moves focus on, so keyboard users are never trapped); Enter keeps the current indentation and increases it after `:` or `{`; optional aligned line-number gutter and a language label. Indentation is preserved exactly in the accepted answer, the summary and any printout — in Python the indentation is the answer. Never execute code: validate structurally only (`data-must` tokens, balanced brackets and quotes, indentation present). Unlocked model answers appear as a formatted code block with a Copy button.

**Formula entry (`numeric`, `symbolic`, `chem`)** — as in Section 4, plus a live preview line under the box rendering what was typed (3/4 → ¾, x^2 → x², H2O → H₂O), a keyboard-reachable symbol palette that does not steal focus, and fraction/index helper buttons that insert a template with the caret in the right place.

**Drawing (`draw`, when `PROFILE.draw`)** — an inline `<canvas>` sketch pad with the background set by `data-canvas` (plain, squared grid, labelled axes, ruled or dotted), a fixed internal resolution scaled for high-DPI screens, and tools: pen in 3 thicknesses, 4–6 colours, eraser, straight-line tool, short text label tool, undo, redo and Clear with confirmation. Use pointer events so it works with mouse, finger and stylus on a tablet or smart board, with `touch-action:none` inside the canvas only so the page does not scroll while drawing. Beside the canvas show the required-labels tick list from `data-labels` and a caption box. Store the result as a PNG data URL so it appears in the completion summary.

**Images (`image`, or optional attachments on any box, when `PROFILE.images`)** — three ways in, all client-side with nothing uploaded anywhere: paste from the clipboard (screenshot, graph, photo), choose file or drag and drop (`image/*` with a visible drop zone), and camera via `capture="environment"` so a student can photograph handwritten working on a tablet. Show a thumbnail with a Remove button, enforce the `data-images` limit (default 2), downscale anything wider than ~1600px and re-encode, and reject non-images or oversized files with a clear message. State on screen that images stay on the student's own device — they are never uploaded, and LISM receives only the fact that an attachment exists, never the image itself.

Because drawings and images cannot be auto-marked, any DOK question using them must have those marks awarded through the teacher override, with the auto-estimate covering only the labels, caption and written reasoning — and the on-screen wording must make that split obvious.

---

## 3. LANGUAGE, SCRIPT AND RTL HANDLING

Set `<html lang>` and `dir` from PROFILE. When `dir:'rtl'`: mirror the whole layout — reference bar, navigation, progress dots, DOK badges, tables and the objective colour bars all flow right-to-left; Next moves left and Previous moves right visually, but the arrow keys keep their logical meaning (→ = next in LTR, ← = next in RTL). Keep code blocks, formulae and numbers `dir:'ltr'` inside RTL text so they don't reverse.

Script-aware word counting: count tokens for Arabic ؀-ۿ, Urdu, Hindi ऀ-ॿ, Chinese/Japanese (character count ÷ 2 as an approximate word equivalent) — do not rely on Latin-only regex.

Arabic normalisation before any comparison: strip tashkeel/diacritics ً-ْ, remove tatweel ـ, unify alef أ إ آ ٱ → ا, ى → ي, ة → ه, unify hamza forms, and normalise Arabic-Indic digits to Western digits.

French/Spanish/Urdu: accent- and diacritic-insensitive comparison for short answers; keep the correct accented spelling in model answers.

The keyword strip and objectives must appear in the lesson's language of instruction; if the lesson is bilingual, show the term and its translation in the same chip.

Never apply the English vowel gibberish heuristic to non-Latin scripts. For non-Latin prose, detect gibberish only by repeated-character runs, single-character spam, and absence of any script-valid word tokens.

---

## 4. MATH AND FORMULA RENDERING (offline-safe)

The file must still work with no internet, so:

- **Primary rendering:** write all display maths as inline MathML or Unicode (x², √, ≤, π, ∫, Σ, θ, °, ½, →) with `<sup>`/`<sub>` and simple CSS fraction spans. This renders in every modern browser with zero dependencies.
- **Optional upgrade:** if `PROFILE.math` is true, attempt to load MathJax from a CDN only as a progressive enhancement, wrapped so that failure is silent and the MathML/Unicode fallback remains visible. The deck must never show broken `$...$` source or a blank space when offline.
- **Symbol palette:** on every numeric, symbolic and mixed box in a maths or science lesson, show a small row of insert-at-cursor buttons — √ x² x³ ^ π ≤ ≥ ≠ × ÷ ± ° θ Δ Σ ∫ ( ) / | fraction (plus → (s) (l) (g) (aq) ⇌ when `PROFILE.chem`). Clicking inserts the symbol at the caret and keeps focus in the box. Also accept ASCII equivalents typed by hand (sqrt, ^2, pi, <=, ->) so a student with a plain keyboard is never blocked.
- **Working-out space:** for maths Main Activity questions, give a larger multi-line box for method plus a separate single-line numeric box for the final answer, and mark method and answer separately in the rubric.

---

## 5. LAYOUT — NO OVERLAPPING (mandatory, verify before finishing)

- Each slide is a flex column with its own internal scroll (`overflow:auto`); content never spills outside its slide or on top of neighbouring content.
- The fixed reference bar and fixed navigation bar sit at the bottom in that order. Measure their combined height in JavaScript and set the slide area's bottom offset from that measured value — recalculate on load, on resize, and whenever the reference bar is collapsed or expanded. Do not hard-code the offset.
- Only the fixed bars may be `position:fixed`; slides use normal flow, not absolutely positioned overlapping blocks.
- Duration labels, badges, score chips and symbol palettes sit inside the flex flow (e.g. `margin-left:auto` in a header row) — never floated or absolutely positioned over text.
- Text must wrap, never clip: allow wrapping in chips, badges and table cells; no fixed heights on text containers; formulae and code blocks scroll horizontally inside their own box rather than widening the slide.
- `clamp()` font sizes so slides fit 1366×768 and 1920×1080 without clipping, reflowing to one column below 900px.
- Check slide by slide at 1366×768 that nothing covers anything — densest slides are the Main Activity, the rubric and the Exit Ticket. If a slide is too tall, reduce padding and font size or move content into the flow; never let it overlap the bars.
- **Inside LISM the deck sits in an iframe with no window chrome of its own** — it must fill its frame at any size and never assume the full viewport.

---

## 6. PERSISTENT REFERENCE BAR

A slim fixed bar visible on EVERY slide, above the navigation, always showing: (1) the lesson keywords as a compact strip; and (2) the three differentiated objectives in shortened form, colour coded — ALL (green), MOST (yellow), SOME (blue). Compact and readable on a smart board and must not cover slide content. Include a small toggle button to collapse or expand it, with the slide area resizing accordingly. In maths/science lessons the strip may include a key formula chip; in language lessons it shows term + translation.

The bar shows the recommended duration of the current stage as text. It never shows a countdown — that comes from LISM, outside the iframe.

---

## 7. MODEL ANSWERS — LOCKED UNTIL THE STUDENT RESPONDS

Model answers live only inside collapsible toggles, and every toggle starts locked and unopenable:

- It cannot open until the student has submitted an accepted answer for that slide's question(s). While locked it reads "🔒 Submit your answer first to unlock the model answer" and clicking does nothing — it must not open, even briefly.
- Starter and Exit Ticket toggles unlock when that slide's boxes are accepted (all 5 blanks on the Exit Ticket). The Main Activity model answers unlock only when all four DOK questions of the student's chosen pathway are accepted — see Section 7b.
- Once unlocked the summary reads "Reveal model answer" and opens normally; it stays closed by default.
- Include a small teacher override ("Teacher: unlock answers") for whole-class feedback. In preview mode (Section 0e) every model answer is freely openable.
- Model answers must show full working for maths, balanced equations for chemistry, runnable code for programming, and correctly accented/diacriticised text for language subjects.

---

## 7b. STUDENT PATHWAY CHOICE, EXTENSIONS AND MARK VISIBILITY

The student always chooses their level. Generate the Main Activity three times over — a full ALL, MOST and SOME pathway, each with its own DOK 1 (2 marks), DOK 2 (3 marks), DOK 3 (3 marks) and DOK 4 (2 marks) questions on the same topic and the same 10-mark rubric, but at different levels of demand and scaffolding:

- **ALL (green)** — more scaffolding: sentence starters, partially completed frames, given values or given code skeletons, one clear step at a time.
- **MOST (yellow)** — the standard grade-level demand with minimal scaffolding.
- **SOME (blue)** — greater demand: less information given, multi-step reasoning, comparison, justification or an unfamiliar context.

**Every pathway is graded out of the full 10 marks. This is non-negotiable:**

- A student who chooses ALL is marked against the same rubric, with the same weightings (DOK 1 = 2, DOK 2 = 3, DOK 3 = 3, DOK 4 = 2), and can earn a genuine 10 / 10. There is no cap, no scaling down, no deduction and no asterisk for choosing ALL — the pathway changes the demand of the questions, never the marks available.
- The mark display must never imply otherwise: show "Main Activity: 8 / 10 (ALL pathway)", never "8 / 10 — reduced level".
- The same applies to MOST and SOME: all three are out of 10 with identical criteria weightings, so the only difference between pathways is the difficulty of the questions.
- Rubric descriptors are applied to the demand of the chosen pathway — "Correct, uses key terms" means correct for the questions that student was actually answering.

**Extensions carry no marks at all** — they are recognised with a certificate. There is no bonus score, no points and no leaderboard:

- The Main Activity total stays exactly 10, whichever pathway was chosen and whether or not any extension was attempted.
- When an extension is submitted, validate it like any other box (word count, key terms, units, structure) and confirm it as completed. Do not score it, and never display an unattempted extension as 0 — show "not attempted".
- Completed extensions unlock an Extension Achievement Certificate (Section 7c) carrying content-specific feedback about what that student actually did.
- The rubric slide and completion summary list the graded 10, the pathway chosen and the extensions completed — as achievements, not as marks.

**Rules for the chooser:**

- At the top of the Main Activity show three large selectable cards — ALL / MOST / SOME — each labelled with its colour and its word, with a one-line description of what that pathway asks for. Nothing is graded until a pathway is chosen, and the choice is shown in the reference bar and the completion summary. Report the chosen pathway to LISM in the `activity_completed` event.
- Only the chosen pathway's four questions are visible; the other two are hidden but available at any time through a "Change level" control. Switching level must never delete work already typed — keep every answer, and state clearly which pathway the current /10 refers to.
- A student may choose any pathway regardless of prior attainment, and may move up or down mid-lesson. Never lock a student out of a level, never label a pathway as "low" or "high", and never auto-assign a level on their behalf.

**Extension tasks per DOK.** Every DOK question has its own optional extension, labelled "Extension — DOK 1/2/3/4", which unlocks only when that DOK question has been submitted and accepted — so a student who finishes early has somewhere to go immediately, without waiting for the rest of the class. Extensions raise demand within the same DOK strand (a harder case, an edge case, a justification, an alternative method). Extensions carry no marks — completing one earns the Extension Achievement Certificate described in Section 7c, and they are never required for anything.

Because there are no timers, nothing unlocks or locks on the clock — extensions unlock on completion of their DOK question, and the model answers unlock on completion of the whole Main Activity.

Offer stretch without pressure: once all four questions in a pathway are accepted, show a quiet "Try the level above" option that reveals the higher pathway's questions as extra practice, marked separately, leaving the graded /10 untouched unless the student explicitly chooses to be graded on the higher pathway instead.

**Model answers stay locked until the whole Main Activity is finished.** All four DOK questions of the chosen pathway must be submitted and accepted before the Main Activity model answers can open. Extensions and the "level above" practice never count towards this — finishing the four graded questions is enough. A part-finished Main Activity keeps every answer toggle sealed and shows "🔒 Complete all four questions to unlock the model answers (3 of 4 done)".

**The student always sees their own marks against the rubric out of 10.** After each accepted response show, next to that question, the rubric level (0–3), the exact descriptor matched (e.g. "Mostly correct") and the marks earned out of that DOK's maximum. In addition:

- A persistent "My mark: x / 10" chip sits in the reference bar, updating live and showing how many criteria are still unmarked.
- The rubric slide shows the full graded table — every criterion with its maximum, the level awarded, the descriptor matched, the marks earned, the running total out of 10 and the percentage — with the chosen pathway named above the table and any completed extensions listed beneath it as achievements, not marks.
- Marks are labelled "estimated — your teacher's mark is final", with the teacher override per criterion recalculating the total instantly.
- Feedback must always say how to gain the missing mark ("You explained the method; add the units to reach 3/3"), never only the score.

---

## 7c. EXTENSION ACHIEVEMENT CERTIFICATE (PDF)

Completing an extension earns recognition, not points. Build an Extension Achievement Certificate the student can save as a PDF, with feedback specific to what that student actually did.

**When it becomes available**

- The "Create my certificate" button appears only once at least one extension has been submitted and accepted, and only after all four graded questions of the chosen pathway are complete; until then it is greyed out with the reason shown.
- The student's name is required — prompt for it if empty, and never produce a certificate with a blank name.
- Include a teacher approval toggle ("Teacher: approve certificate") and a one-line teacher comment field, so the certificate is issued by the teacher rather than self-awarded.
- Only extensions genuinely completed are named; never list a skipped extension, and never issue the certificate for the graded task alone.

**What goes on it**

- Heading — "Certificate of Achievement · Extension Challenge" — with an editable school or class name field.
- Student name, class, subject, grade, week, [TOPIC NAME] and the date.
- The extension(s) completed, named with their DOK strand, e.g. "Extension — DOK 3: Application".
- Content-specific commendation of 2–3 sentences assembled from real signals in that student's work — which extension(s) they completed, which lesson keywords they used correctly, the rubric levels reached, and whether the answer contained code, a calculation, a balanced equation, a diagram or an evaluation. Write them as topic-specific statements, e.g. "Aisha extended her work on classes in Python by designing a Loan class linking books to members, and justified her structure using encapsulation, method and instance accurately." Generate a small bank of such statements keyed to the topic and each DOK strand, and select from it based on what was actually detected.
- Never fabricate — no praise for work not submitted, no invented scores, no claims the file cannot verify. Partial work is described plainly ("recognised for extending DOK 2: Skill").
- A forward-looking line naming what to try next in this topic, so the certificate teaches as well as rewards.
- Teacher signature line and date, with room to sign the printed copy.
- No marks anywhere on the certificate — this replaces bonus scoring entirely.

**How the PDF is produced (offline-safe, no dependencies)**

- Render the certificate as an on-screen A4 landscape panel with a decorative border, the lesson's colour scheme and large readable type, so the student sees exactly what they will get.
- Primary export: a "Save as PDF" button calling `window.print()` with a print stylesheet scoped to the certificate alone — `@page { size: A4 landscape; margin: 0 }`, everything else `display:none`, no internal page breaks, `print-color-adjust:exact`. The browser's own "Save as PDF" destination creates the file, so it works offline with nothing installed.
- Secondary export: "Download as image", drawing the certificate to a canvas and saving a PNG for browsers with a restricted print dialogue.
- Optional progressive enhancement: if a PDF library is reachable from a CDN, offer a one-click PDF download — but the print route must remain fully functional offline and the file must never depend on the library loading.
- The certificate follows `PROFILE.lang` and `PROFILE.dir`, so an Arabic lesson produces a fully right-to-left certificate with the commendation written in Arabic.
- Everything is generated on the student's own device; nothing is uploaded.

---

## 8. SLIDE STRUCTURE (exactly 10 slides)

Each slide carries `data-stage="<manifest id>"` and emits `stage_viewed` when shown.

**Slide 1 — TITLE** (`title`): [TOPIC NAME], subject, grade and week on a clean title layout.

**Slide 2 — KEYWORDS & OBJECTIVE** (`keywords`, Recommended Duration: 2 minutes): keywords as a prominent vocabulary strip; the full lesson objective in one sentence; the full ALL / MOST / SOME success criteria in student-friendly "I can…" language.

**Slide 3 — STARTER** (`starter`, Recommended Duration: 5 minutes + feedback): one open-ended review question about [PREVIOUS LESSON TOPIC]. Instruction: "Your answer must use at least 1 key term from this lesson." One response box of the profile-appropriate type. Note: "Feedback: teacher reviews responses and students may explain their answers." Model answer in the locked toggle.

**Slide 4 — LEARNING OBJECTIVES** (`objectives`): ALL / MOST / SOME success criteria, colour coded green / yellow / blue, in "I can…" language, with a line telling students they will choose which level to attempt in the Main Activity and may change it at any time.

**Slide 5 — MAIN TEACHING (I DO)** (`main-teaching`, Recommended Duration: 10 minutes): the topic in 3 clear parts with one labelled diagram or simple interactive visual (click-to-reveal cards, canvas figure, worked example stepper for maths, labelled apparatus for science). Minimal text, visuals dominant. A short "Try it" discussion question at the bottom.

**Slides 6–7 — MAIN ACTIVITY** (`main-activity`, then `rubric`) (Recommended Duration: 10 minutes + feedback, 10 marks): the student first chooses their pathway — ALL, MOST or SOME — and then works through that pathway's DOK 1 Recall (2 marks), DOK 2 Skill (3 marks), DOK 3 Application (3 marks) and DOK 4 Evaluation (2 marks) questions, each with its own optional extension that unlocks on submission. Generate all three pathways in full, as specified in Section 7b. Choose the answer type per question — typically short/numeric for DOK 1, numeric/symbolic/code/draw/mixed for DOK 2, mixed for DOK 3, prose for DOK 4 — and where the subject's real answer is a diagram, graph, circuit, map or handwritten working, use `draw` or `image` (or `mixed` with an explanation beside it) rather than forcing a written description. Instruction: "Answers must include at least 2 key terms" (for prose parts; for numeric/symbolic parts require correct method or units instead, and say so on screen). Note: "Feedback: teacher gives feedback on responses and students may defend their work." Slide 7 shows the rubric.

**Marking as the student submits (mandatory):** the moment a DOK response is accepted, mark it against the rubric and show next to that question the rubric level (0–3), the descriptor matched (e.g. "Mostly correct") and marks earned out of that DOK's maximum. Mirror every mark into a "Your mark" column in the slide 7 rubric table, update a running total out of 10 live in the rubric header and the navigation bar, and flag criteria still unmarked. **Emit `student_submitted` at the same moment**, carrying `dok`, `rubricLevel`, `mark`, `maxMark` and `keywordsUsed`, so the teacher's dashboard shows the same picture the student sees. Marking basis depends on answer type: correctness against the answer key for numeric, symbolic, chem, short and code (full marks = correct with valid method/units/structure; partial = right method wrong value, or right value wrong units/sig figs; low = attempt only); depth, key-term coverage and reasoning for prose and the prose half of mixed; ticked criteria plus justification for checklist; for draw and image, auto-mark only the labels, caption and reasoning and show "awaiting teacher mark" for the diagram or attachment rather than a guessed score. Label the total "estimated — teacher's mark is final" and give the teacher a 0/1/2/3 override selector per DOK that recalculates the total.

**MAIN TASK MARKING RUBRIC (10 marks total):** DOK 1 Knowledge/Recall — 3: Correct, uses key terms, 2: Mostly correct, 1: Partial, 0: Blank or gibberish — /2. DOK 2 Skill/Accuracy — 3: Fully correct and explained, 2: Mostly correct, 1: Partial and weak, 0: Blank or gibberish — /3. DOK 3 Application — 3: Clear reasoning, 2: Mostly applied, 1: Partial, 0: Blank or gibberish — /3. DOK 4 Evaluation — 3: Well-justified, 2: Reasonable, 1: Limited, 0: Blank or gibberish — /2. TOTAL — /10.

**Slide 8 — CONNECTION LINK** (`connection`, Recommended Duration: 3 minutes) — TEACHER'S CHOICE: three tabs at the top — "UAE Link", "AI Link", "Cross-Curricular Link"; clicking one reveals that version and hides the others. Generate all three: (1) UAE Link — one sentence connecting the topic to life, industry or culture in the UAE; (2) AI Link — one sentence on how AI or emerging technology relates to or is transforming this topic; (3) Cross-Curricular Link — one sentence connecting the topic to another school subject. Each has a short student response box and a 3-option poll that tallies live when clicked. Warm gold or green accent.

**Slide 9 — EXIT TICKET** (`exit-ticket`, Recommended Duration: 5 minutes + feedback): 5 short questions testing this lesson's objectives — fill-in-the-blank for terminology subjects, or 5 quick numeric/symbolic/chem items for maths and science. Each has its own box with profile-appropriate validation and its own `data-qid`. Instruction: "Use at least 1 key term per answer" (or "Show units in every answer" for numeric lessons). Note: "Feedback: teacher reviews exit responses and students may explain their thinking." Model answers in the locked toggle (unlocks after all 5 are submitted).

**Slide 10 — REFLECTION & COMPLETION REPORT** (`reflection`, Recommended Duration: 5 minutes): 3-2-1 — 3 things you learned, 2 things you want to explore further, 1 thing you are still unsure about — three boxes with minimum word counts, followed by the student completion report in Section 8b.

---

## 8b. STUDENT COMPLETION REPORT (mandatory, on the final slide)

Built only from what actually happened — never invented, never padded:

- **Completion status** and stages completed, e.g. "9 of 10 sections completed".
- **Estimated Main Activity score out of 10**, broken down per DOK, with the pathway named ("8 / 10 · MOST pathway"), labelled *estimated — your teacher's mark is final*.
- **Participation summary:** responses submitted, extensions completed, diagrams drawn, images attached, poll answered.
- **Keywords used:** which of the lesson's keywords the student actually used, as ticked chips, and which they did not.
- **Time spent** — taken from LISM's `time_update` command. The deck has no timer of its own, so standalone (no LISM) **omit this line entirely rather than inventing a number**.
- **Teacher review pending** — list anything awaiting a human mark (diagrams, attachments, criteria under teacher override), with the wording "Your teacher will review and confirm your final mark."

Emit `activity_completed` with the same figures at the moment the report is first shown.

---

## 9. DESIGN RULES

One consistent colour scheme; DOK badges colour coded (DOK1 green, DOK2 blue, DOK3 amber, DOK4 red); persistent reference bar on every slide; minimal text with large smart-board fonts; the recommended duration shown beside every section title and **no timer or countdown of any kind**; model answers only inside locked collapsible toggles; smooth transitions; responsive full-screen layout with no overlapping elements; strong colour contrast and colour never the only signal (pair each objective colour with the word ALL/MOST/SOME and each DOK colour with its number); completion report at the end.

---

## 10. TIMING (metadata and guidance only)

50-minute period — Keywords & Objectives 2 minutes, Starter 5 minutes, Main Teaching 10 minutes, Main Activity 10 minutes, Connection Link 3 minutes, Exit Ticket 5 minutes, Reflection 5 minutes, plus 10 minutes reserved across the Starter, Main Activity and Exit Ticket for teacher feedback and for students to explain or defend their work.

These figures appear in two places and nowhere else: as `durationSeconds` in the manifest (so LISM's dashboard can show and use them), and printed beside each slide title as guidance. They are never counted down inside the deck, never enforced, and never used to lock anything.

---

## 11. SELF-CHECK BEFORE YOU FINISH

State briefly that you have verified:

**LISM integration** — exactly one valid `lism-manifest` JSON block with 10 stages whose ids match every slide's `data-stage` and every event's `stageId`; `activity_ready` emitted on load inside LISM and the first slide shown when standalone; `start_stage`, `stage_ended`, `pause`, `resume`, `lock`, `unlock`, `set_config` and `time_update` all handled, unknown commands ignored silently; **`student_submitted` emitted on every accepted answer** with `data-qid`, stage id, mark, DOK and keywords — the deck reports to the teacher dashboard rather than keeping marks to itself; `?preview=1` gives Previous/Next plus a stage counter, unlocks every stage, and emits nothing at all; the deck opens standalone in a browser and works fully offline with no LISM present.

**Pacing** — no timers, countdowns or time-based pacing logic anywhere in the file; only recommended durations as manifest metadata and as text beside section titles; pause and resume preserve every typed answer.

**Teacher settings** — copy-paste protection off by default and applied only to answer boxes when enabled; focus monitoring off by default, one warning per physical departure, maximum 3, and the deck never locks on its own authority.

**Educational framework** — exactly 10 slides; nothing overlaps at 1366×768 and the deck fills its iframe at any size; arrow keys inert while typing; all three ALL/MOST/SOME pathways generated in full with a working chooser that preserves typed work when switching; every pathway including ALL graded out of the full 10 with no cap or scaling; a per-DOK extension that unlocks on submission, carries no marks, and produces a content-specific achievement certificate that saves as an A4 landscape PDF offline; Main Activity model answers sealed until all four graded questions are accepted; the student's marks against the rubric visible out of 10 at all times; every other model-answer toggle locked until submission; each DOK marked on submit with a live total out of 10 and teacher override; every answer box validated by its declared type with a specific rejection reason; code boxes take Tab as indentation without trapping focus and preserve whitespace; the formula preview renders what was typed; the sketch pad works with mouse, finger and stylus without scrolling the slide, and undo/clear behave; paste, file-choose, drag-drop and camera capture all attach an image with limits enforced; the completion report shows only real figures and omits time spent when standalone; math/chem/code/draw/image/RTL features present and working offline as required by the subject profile.
