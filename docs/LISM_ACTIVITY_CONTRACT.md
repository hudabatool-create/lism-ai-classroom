# LISM Activity Contract (v2)

The single agreement between **an activity's HTML** and **the LISM AI Classroom platform**. Both sides must be changed together, so both sides read this file:

- Master prompts (Interactive Lesson Deck, Interactive Worksheet) generate HTML that obeys this contract.
- Platform code that implements it: `backend/app/services/manifest_service.py`, `frontend/src/app/join/[code]/page.tsx`, `frontend/src/app/(dashboard)/dashboard/live/[sessionId]/page.tsx`.

**Design rule: an activity must still work perfectly when opened directly in a browser with no LISM around it.** Every integration point below is additive and guarded by "am I inside LISM?". A teacher who downloads the HTML and opens it offline gets a fully working, self-paced activity.

---

## 1. Detecting LISM

```js
const IN_LISM = window.parent !== window;
```

That is the whole test. When `IN_LISM` is false: run standalone (self-paced, show all sections, no events). When true: hand pacing to LISM and report events.

LISM serves the activity in an iframe from the backend's `/api/activities/{id}/raw`, so the activity and the LISM page are on **different origins**. All messaging is `postMessage` — never assume shared DOM or storage access.

---

## 2. The manifest block (activity → platform, at intake)

Every activity must embed exactly one inert JSON block. LISM parses it **server-side at upload/generate time**, without executing the page:

```html
<script type="application/json" id="lism-manifest">
{
  "lessonType": "lesson-deck",
  "subject": "Chemistry",
  "grade": "9",
  "week": "Week 4",
  "topic": "Balancing Equations",
  "learningObjectives": { "all": "…", "most": "…", "some": "…" },
  "keywords": ["reactant", "product", "coefficient", "conservation of mass"],
  "dok": [
    { "level": 1, "label": "Recall",     "marks": 2 },
    { "level": 2, "label": "Skill",      "marks": 3 },
    { "level": 3, "label": "Application","marks": 3 },
    { "level": 4, "label": "Evaluation", "marks": 2 }
  ],
  "deliveryMode": "lesson",
  "sessionType": "lesson",
  "stages": [
    { "id": "title",        "label": "Title",           "type": "title",        "durationSeconds": 60,  "sequentialLock": false, "marks": null },
    { "id": "keywords",     "label": "Keywords & Objective", "type": "keywords", "durationSeconds": 120, "sequentialLock": false, "marks": null },
    { "id": "starter",      "label": "Starter",         "type": "starter",      "durationSeconds": 300, "sequentialLock": true,  "marks": null },
    { "id": "main-activity","label": "Main Activity",   "type": "main-activity","durationSeconds": 600, "sequentialLock": true,  "marks": 10 },
    { "id": "exit-ticket",  "label": "Exit Ticket",     "type": "exit-ticket",  "durationSeconds": 300, "sequentialLock": true,  "marks": null }
  ]
}
</script>
```

Rules:

- **`id` is the contract.** Every event the activity sends references a `stages[].id`. Ids must be stable, lowercase-hyphenated, and unique.
- **One stage per navigable section**, in presentation order. A deck slide or worksheet section = one stage.
- **`durationSeconds` is the recommended duration only** — LISM's dashboard displays it and uses it as the default countdown length. The activity never counts it down itself (see §4).
- `sequentialLock: true` means students should not reach this stage before the teacher starts it.
- `marks` is the stage's mark total (`10` for the Main Activity/Task, `null` elsewhere).
- `deliveryMode` (`lesson` | `homework`) is the activity's own wording/pacing axis. `sessionType` (`lesson` | `practice` | `assessment`) is LISM's enforcement axis. **They are deliberately separate fields** — do not merge them.

Missing or unparseable manifest ⇒ the platform falls back to a single "unmanaged" stage. The activity still runs, but there is no per-stage pacing, no per-stage progress, and no meaningful live dashboard. **A manifest is what makes an activity a first-class LISM activity.**

---

## 3. Messages

### 3.1 Platform → activity (commands)

```js
{ type: "lism:command", command: "<name>", ...payload }
```

| `command` | Payload | Activity must |
|---|---|---|
| `start_stage` | `stage` (manifest stage object), `stageIndex`, `serverTime` | Show only that stage; enable its inputs |
| `stage_ended` | — | Show "Waiting for your teacher…"; disable that stage's inputs |
| `pause` | — | Freeze interaction; show a paused notice; keep all typed work |
| `resume` | — | Unfreeze; restore the previous view exactly |
| `lock` | `reason` | Disable every input; show the lock reason. Not dismissible by the student |
| `unlock` | — | Re-enable inputs (teacher cleared the lock) |
| `set_config` | `copyPasteProtection` (bool), `focusMonitoring` (bool), `maxWarnings` (int) | Apply teacher settings (§6, §7) |
| `time_update` | `elapsedSeconds`, `remainingSeconds` | Store for the completion report (§5). Display only if LISM asks |

Unknown commands must be **ignored silently** — never throw, never break the activity. This lets the platform add commands without regenerating activities.

### 3.2 Activity → platform (events)

```js
window.parent.postMessage({ type: "lism:event", event: "<name>", ...payload }, "*");
```

| `event` | Payload | When |
|---|---|---|
| `activity_ready` | `stageCount` | Once, after the activity has parsed its own manifest and is ready for commands |
| `stage_viewed` | `stageId` | Student's view moved to this stage |
| `response_update` | `stageId`, `questionId`, `charCount`, `wordCount` | Student is working — **throttle to at most once every 2s per box**. Never send raw keystrokes |
| `student_submitted` | `stageId`, `questionId`, `correct`, `answer`, `mark`, `maxMark`, `dok`, `rubricLevel`, `keywordsUsed` | A box was submitted **and accepted** |
| `stage_completed` | `stageId`, `marksEarned`, `maxMarks` | Every required box in the stage is accepted |
| `activity_completed` | `pathway`, `totalMarks`, `maxMarks`, `stagesCompleted`, `keywordsUsed`, `extensionsCompleted` | Final stage accepted / student pressed Finish |
| `help_requested` | `stageId`, `questionId` | Student clicked "I need help" inside the activity |
| `focus_warning` | `stageId`, `warningNumber`, `kind` | Activity's own focus monitor fired (§7) |

**Required for the live dashboard to work at all: `student_submitted`.** That single event is what creates a response record in LISM. An activity that validates and marks internally but never sends this will display correctly and report nothing — the exact bug found in testing with v8/v6.

Compatibility note: the platform also still accepts a legacy flat message `{ type: "lism-activity-response", correct, answer }` from pre-contract activities. Do not emit this in new activities; emit `student_submitted`.

### 3.3 Minimal reference implementation

Paste-ready, and the shape every generated activity should contain:

```js
const IN_LISM = window.parent !== window;
const LISM = {
  config: { copyPasteProtection: false, focusMonitoring: false, maxWarnings: 3 },
  elapsedSeconds: null,
  preview: new URLSearchParams(location.search).get('preview') === '1',

  emit(event, payload = {}) {
    // Preview mode must never create student data.
    if (!IN_LISM || this.preview) return;
    window.parent.postMessage({ type: 'lism:event', event, ...payload }, '*');
  }
};

window.addEventListener('message', (e) => {
  const d = e.data || {};
  if (d.type !== 'lism:command') return;
  switch (d.command) {
    case 'start_stage':  showStage(d.stage.id); break;
    case 'stage_ended':  showWaiting(); break;
    case 'pause':        setFrozen(true); break;
    case 'resume':       setFrozen(false); break;
    case 'lock':         applyLock(d.reason); break;
    case 'unlock':       clearLock(); break;
    case 'set_config':   Object.assign(LISM.config, d); applyConfig(); break;
    case 'time_update':  LISM.elapsedSeconds = d.elapsedSeconds; break;
    // Unknown commands are ignored on purpose.
  }
});

if (IN_LISM) {
  LISM.emit('activity_ready', { stageCount: STAGES.length });
} else {
  showStage(STAGES[0].id);   // standalone: self-paced from the first stage
}
```

---

## 4. Pacing — the activity owns none of it

Inside LISM the teacher controls Start / Pause / Resume / End / Next stage. The activity therefore must contain:

- **No** `setInterval` / `setTimeout` / `Date`-based logic used for pacing.
- **No** countdown display, clock, progress ring or timer UI.
- **No** auto-advance, auto-lock, or greying out because time passed.
- **No** timer started by first keystroke, focus or submission.

It contains instead:

- `durationSeconds` per stage in the manifest (metadata only).
- The recommended duration printed beside each stage title as guidance ("Starter · Recommended: 5 minutes").

The only countdown a student ever sees is the synchronised one LISM renders outside the iframe. `setTimeout` for non-pacing UI (a toast auto-hiding, a debounce) is fine.

---

## 5. Completion report

At the end of the activity the student sees a report built from what actually happened — never invented:

- Completion status and stages completed (e.g. "9 of 10").
- Estimated Main Activity/Task score out of 10, per-DOK, labelled *estimated — your teacher's mark is final*.
- Participation summary: responses submitted, hints used, diagrams drawn, images attached.
- Which lesson keywords the student actually used.
- **Time spent — taken from LISM's `time_update`**, since the activity has no timer of its own. Standalone (no LISM), omit the line rather than inventing a number.
- "Teacher review pending" for anything awaiting a human mark (diagrams, images, overrides).

The same data goes out in the final `activity_completed` event.

---

## 6. Copy & paste protection (teacher-configurable)

Off by default; enabled by `set_config { copyPasteProtection: true }`. When on, inside answer inputs:

- Block `copy`, `cut`, `paste`, `contextmenu`, and drag-and-drop of text.
- Show a short, non-alarming notice explaining students type their own answers.

Never block browser-level accessibility, never disable keyboard navigation, and keep the image-attachment paste path working when the activity's profile uses `image` answers (a photo of handwritten working is not plagiarism) — unless protection explicitly covers it.

---

## 7. Focus monitoring (teacher-configurable)

LISM already runs its own focus monitor on the student page and owns the authoritative violation count, the 3-strike lock and the teacher notification. The activity's role is secondary:

- Only monitor when `set_config { focusMonitoring: true }`.
- Watch tab switching (`visibilitychange`), window blur/focus.
- Collapse one physical departure into **one** warning — `blur` and `visibilitychange` both fire for the same event.
- Emit `focus_warning` with an incrementing `warningNumber`; do not lock on your own authority. **LISM sends `lock` when the limit (`maxWarnings`, default 3) is reached** — a single source of truth for locking.

---

## 8. Teacher preview

Teachers open `/api/activities/{id}/raw?preview=1` to review a lesson before launching.

In preview mode the activity must:

- Show Previous / Next controls and a stage counter ("4 / 10"), so every stage can be inspected without LISM pacing.
- Ignore `sequentialLock` — all stages reachable.
- **Emit no events at all** and create no student data (see `LISM.emit` guard above).
- Show a clear "Preview — not a live lesson" banner.

---

## 9. Checklist for a new activity

1. Exactly one `<script type="application/json" id="lism-manifest">` block, valid JSON, one stage per section, stable ids.
2. `activity_ready` on load when inside LISM; first stage shown when standalone.
3. Handles `start_stage`, `stage_ended`, `pause`, `resume`, `lock`, `unlock`, `set_config`, `time_update`; ignores anything else.
4. Emits `student_submitted` on every accepted answer, with `stageId` matching a manifest id. **Verify a response reaches the teacher dashboard.**
5. No pacing timers anywhere; recommended durations shown as text only.
6. `?preview=1` gives Prev/Next navigation and emits nothing.
7. Opens standalone in a browser and works fully with no LISM present.

---

## Platform support status

| Contract feature | Platform status |
|---|---|
| Manifest parsing, stages | Implemented (`manifest_service.py`) |
| `start_stage`, `stage_ended` | Implemented (`join/[code]/page.tsx`) |
| `student_submitted` → response record | Implemented |
| Legacy `lism-activity-response` | Implemented (back-compat) |
| Focus monitoring + 3-strike lock + teacher alert | Implemented, LISM-side, now driven by the teacher's `focus_monitoring` setting (defaults on for an assessment) |
| `pause` / `resume` | Implemented — `POST /api/sessions/{id}/stage/pause` and `/resume`, Pause/Resume on the dashboard, relayed to the activity. Remaining time is banked on pause and resumed from, so the countdown never loses or gains time |
| `set_config` (copy-paste, focus toggles) | Implemented — `PATCH /api/sessions/{id}/settings`, toggles on the dashboard, broadcast live and relayed as `set_config` with no reload |
| `time_update` | **Not yet** |
| `response_update`, `stage_completed`, `activity_completed`, `help_requested`, `focus_warning` | **Not yet consumed** — safely ignored today |
| `?preview=1` with Prev/Next | Activity-side only; no platform work needed |

Events the platform does not yet consume are harmless: activities emit them now, and the dashboard can start using them later **without regenerating a single activity**. That is why the contract is defined in full ahead of the platform catching up.
