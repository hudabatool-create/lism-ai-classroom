# LISM AI Classroom — Development Status Report

**Reviewed:** 25 July 2026
**Basis:** direct read of the current source tree (`backend/app/**`, `frontend/src/**`). No roadmap, no future plans — current state only.

---

## Global constraint that affects every "demonstrable" answer

`backend/app/services/data_store.py` is an **in-memory Python dict store**. It has no database behind it. Every teacher account, activity, session, student and response is lost when the backend process restarts. `backend/db/supabase_schema.sql` exists but nothing in the running code reads or writes to Supabase.

So "demonstrable right now" below means: *demonstrable after starting both servers and re-creating the data in that same run.* Nothing survives a restart, and nothing can be demoed on two machines at once unless they hit the same backend process.

Also note: the frontend calls `http://localhost:8000` by default (`frontend/src/lib/api.ts` line 1), so students must be on the same machine or the network must be reachable at that address.

---

## Status Table

| # | Feature | Status |
|---|---------|--------|
| 1 | Teacher Sign Up | ✅ Fully Functional |
| 2 | Teacher Login | ✅ Fully Functional |
| 3 | Teacher Dashboard | 🟡 Partially Functional |
| 4 | My Activities | 🟡 Partially Functional |
| 5 | Upload HTML Activity | ✅ Fully Functional |
| 6 | Upload ZIP Activity | ❌ Not Implemented |
| 7 | AI Activity Generator | 🟡 Partially Functional |
| 8 | Prompt Library | ❌ Not Implemented |
| 9 | Activity Templates | ❌ Not Implemented |
| 10 | Preview Activity | ✅ Fully Functional |
| 11 | Start Live Session | ✅ Fully Functional |
| 12 | QR Code Generation | ✅ Fully Functional |
| 13 | Join Link | ✅ Fully Functional |
| 14 | Activity Code | ✅ Fully Functional |
| 15 | Student Join Page | ✅ Fully Functional |
| 16 | Live Classroom Dashboard | 🟡 Partially Functional |
| 17 | Live Student Responses | 🟡 Partially Functional |
| 18 | Student Progress Tracking | ❌ Not Implemented |
| 19 | WebSocket Updates | 🟡 Partially Functional |
| 20 | Classroom Controls | 🟡 Partially Functional |
| 21 | Basic Analytics | 🟡 Partially Functional |
| 22 | PDF Export | ✅ Fully Functional |
| 23 | Excel Export | ❌ Not Implemented |
| 24 | CSV Export | ✅ Fully Functional |
| 25 | Session History | 🟡 Partially Functional |
| 26 | Activity Reuse | 🟡 Partially Functional |
| 27 | Duplicate Activity | ❌ Not Implemented |
| 28 | Teacher Security (data isolation) | 🟡 Partially Functional |
| 29 | AI Insights | ⚪ UI Only / Placeholder |
| 30 | Activity Library | ⚪ UI Only / Placeholder |
| 31 | Settings | ⚪ UI Only / Placeholder |

**Totals:** 11 fully functional · 11 partial · 3 placeholder · 6 not implemented.

---

## Feature-by-Feature Detail

### 1. Teacher Sign Up — ✅ Fully Functional

**Implemented.** `POST /api/auth/signup` (`routes/auth.py`). Validates email format via pydantic `EmailStr`, rejects duplicate emails with a 400, hashes the password with PBKDF2-SHA256 / 100,000 iterations and a random 16-byte salt (`core/security.py`), returns a signed JWT. Frontend form at `/signup` stores the token in `localStorage` and redirects to the dashboard.

**Missing.** No email verification. No password strength rule of any kind — a one-character password is accepted. No rate limiting on the endpoint. `hash_password` uses PBKDF2 rather than bcrypt/argon2 (a deliberate scaffold choice noted in the file's own comment, but it is weaker than the production standard).

**Demonstrable now?** Yes.

---

### 2. Teacher Login — ✅ Fully Functional

**Implemented.** `POST /api/auth/login`. Constant-time hash comparison via `hmac.compare_digest`. Issues a 7-day HS256 JWT. `AuthGuard.tsx` redirects any unauthenticated visit to a `/dashboard/*` route back to `/login`. Log out clears the token and redirects.

**Missing.** JWT secret defaults to the literal string `"dev-secret-change-me"` (`core/config.py` line 9) — if `.env` is absent, every token is forgeable by anyone who reads the repo. No refresh tokens, no server-side revocation (logging out only clears the browser copy; the token stays valid for 7 days). Token is in `localStorage`, which is XSS-readable. No password reset, no lockout after repeated failures.

**Demonstrable now?** Yes.

---

### 3. Teacher Dashboard — 🟡 Partially Functional

**Implemented.** `/dashboard` overview renders three live counts (Activities, Sessions Run, Active Now) fetched from the API, quick-action buttons, and a list of currently active sessions linking through to the live view. Sidebar navigation with all nine items, active-route highlighting, and log out.

**Missing.** Three of the nine sidebar destinations (AI Insights, Activity Library, Settings) are placeholder components. There is no "Prompt Library", "Activity Templates" or "Session History" nav item at all — the MVP spec lists all three. No notifications. No dark/light toggle control (the CSS supports `dark:` variants but nothing switches the class).

**Demonstrable now?** Yes, with the caveat that a third of the nav leads to "coming soon" screens.

---

### 4. My Activities — 🟡 Partially Functional

**Implemented.** `GET /api/activities` returns only the calling teacher's rows (filtered by `teacher_id` in `data_store.list_activities`), newest first. Card grid shows title, subject, grade, type, an AI-Generated / Uploaded badge, a Preview link and a Start Activity button.

**Missing.** The MVP calls for view, **search, edit, duplicate, delete, organize**. Only *view* exists. There is no `PATCH`, `DELETE`, or duplicate endpoint anywhere in `routes/activities.py`. No search box, no filter, no folders or tags.

**Demonstrable now?** Yes for listing/launching; no for search, edit, duplicate, delete.

---

### 5. Upload HTML Activity — ✅ Fully Functional

**Implemented.** `POST /api/activities/upload` accepts a multipart form with title/subject/grade/type plus the file, decodes as UTF-8, stores the HTML string against the teacher, and serves it back at `GET /api/activities/{id}/raw` as `text/html`. Teacher never touches Netlify or GitHub — the stated goal is met for single-file HTML.

**Missing.** Extension check is by filename only (`.html`/`.htm`) — no content-type or content validation. No file size limit. No sanitisation of the uploaded HTML: uploaded JavaScript runs with full access to the `/api/activities/...` origin. No CSP header on the raw route.

**Demonstrable now?** Yes.

---

### 6. Upload ZIP Activity — ❌ Not Implemented

**Implemented.** Nothing. The backend explicitly rejects it: `"Only .html/.htm files are supported in this scaffold"` (`routes/activities.py` line 27). The frontend file input is restricted to `accept=".html,.htm"`.

**Missing.** ZIP unpacking, asset storage, path rewriting, and a static-file serving route — the entire feature.

**Demonstrable now?** No. Attempting it produces a 400 error.

---

### 7. AI Activity Generator — 🟡 Partially Functional

**Implemented.** The form collects all seven fields the spec asks for (subject, grade, topic, objectives, activity type from a 17-item dropdown, difficulty, time limit). `POST /api/activities/generate` calls OpenAI `gpt-4o-mini` when `OPENAI_API_KEY` is set, instructing it to return a self-contained HTML file that posts a `lism-activity-response` message to `window.parent`. The result is saved as an activity and immediately previewable.

**Missing.** **No API key is configured**, so in practice this path never runs — `generate_activity_html` falls through to `_canned_template`, which always produces the *same* 4-option multiple-choice question with placeholder text ("A distractor about {subject}", "The correct explanation of {topic}"). It ignores `objectives` entirely. So the generator currently generates a stub, not a lesson. The OpenAI failure path is a bare `except Exception: return None` — a bad key, a rate limit and a network outage all silently degrade to the canned template with no message to the teacher. There is also no way to paste your own master prompt, which the MVP explicitly requires.

**Demonstrable now?** The *flow* is demonstrable. The *AI* is not — you will get the canned stub. Do not demo this to teachers as "AI generation" without a key set.

---

### 8. Prompt Library — ❌ Not Implemented

**Implemented.** Nothing. No route, no page, no nav item, no `prompts` collection in the data store.

**Missing.** Save, categorise, favourite, and reuse master prompts — and the "paste your own prompt" field in the generator that would feed it. This is the feature that connects your existing master prompt workflow to the platform, and none of it exists.

**Demonstrable now?** No.

---

### 9. Activity Templates — ❌ Not Implemented

**Implemented.** Nothing. The `ACTIVITY_TYPES` array in the generator page is a dropdown of *labels* passed as a string into the prompt — it is not a template library. No template is stored, previewed, or instantiated.

**Missing.** The eleven templates the MVP lists (Starter, Main Lesson, Exit Ticket, Quiz, Poll, Reflection, Coding, Escape Room, Matching, Flashcards, AI Chat) as selectable, previewable starting points.

**Demonstrable now?** No.

---

### 10. Preview Activity — ✅ Fully Functional

**Implemented.** Preview links on the activities grid, the post-generate panel and the post-upload panel all open `{API}/api/activities/{id}/raw` in a new tab, rendering the real HTML the student will see.

**Missing.** Preview is not embedded in the dashboard (it leaves the app in a new tab). No "preview as student" mode that also exercises the response-posting path.

**Demonstrable now?** Yes.

---

### 11. Start Live Session — ✅ Fully Functional

**Implemented.** `POST /api/activities/{id}/launch` verifies the activity belongs to the caller, creates a session with a collision-checked 6-character code, and returns it with a join URL. Launch buttons exist on both My Activities and Live Classroom; both redirect to `/dashboard/live/{sessionId}`.

**Missing.** No guard against launching multiple concurrent sessions for the same activity. Session has no `started_at` distinct from `created_at`, no scheduled start, no timer.

**Demonstrable now?** Yes.

---

### 12. QR Code Generation — ✅ Fully Functional

**Implemented.** `GET /api/sessions/{id}/qrcode.png` renders a PNG of the join URL server-side via the `qrcode` library and streams it; the live page displays it as a 144px image.

**Missing.** No download or print button for projecting the code. The endpoint is intentionally unauthenticated (documented in a comment) because a plain `<img>` tag can't send a bearer header — acceptable, since it only encodes the shareable join URL.

**Demonstrable now?** Yes.

---

### 13. Join Link — ✅ Fully Functional

**Implemented.** Built server-side as `{FRONTEND_ORIGIN}/join/{CODE}`, displayed on the live page as a clickable link with a copy-to-clipboard button.

**Missing.** `frontend_origin` defaults to `http://localhost:3000`, so the generated link only works on the teacher's own machine until that env var is set to a real host. This is the single biggest blocker to a real classroom demo.

**Demonstrable now?** Yes locally. No across devices without configuring `FRONTEND_ORIGIN` and `NEXT_PUBLIC_API_BASE_URL`.

---

### 14. Activity Code — ✅ Fully Functional

**Implemented.** 6-character uppercase alphanumeric, regenerated on collision. Displayed in large monospace on the live page with a copy button. `/join` page accepts a typed code, uppercases it, and routes to the session. Backend uppercases on lookup, so entry is case-insensitive.

**Missing.** Codes are never retired — an ended session's code stays permanently reserved. Character set includes `0`/`O` and `1`/`I`, which students will misread when it's on a projector.

**Demonstrable now?** Yes.

---

### 15. Student Join Page — ✅ Fully Functional

**Implemented.** `/join/{code}` fetches session info, shows the activity title, collects Name / Grade / Section, posts to `POST /api/join/{code}`, and on success swaps to a full-screen iframe of the activity. No student account required. Rejects unknown codes with a clear message and blocks joining an ended session.

**Missing.** Only Name is `required`; Grade and Section can be left blank despite the spec listing all three. No duplicate-name handling — two students called "Ali" become two indistinguishable rows. No rejoin: refreshing the page loses `studentId` (held only in React state, never persisted), so the student is re-added as a brand-new student and their earlier responses orphan.

**Demonstrable now?** Yes.

---

### 16. Live Classroom Dashboard — 🟡 Partially Functional

**Implemented.** Shows activity title, session code, active/ended status, the join panel (QR + code + link), three stat cards (Students Joined, Responses, Completion %), a live student list, and a live response feed. Both lists update over WebSocket with no refresh.

**Missing.** Against the MVP list: **students currently working**, **students finished**, **participation percentage**, **activity timer** and **session status beyond active/ended** are all absent. The dashboard cannot answer "who is stuck" — it only knows who joined and who has submitted. "Completion" is computed as `responses / students`, which exceeds 100% the moment any student submits twice.

**Demonstrable now?** Yes for joins and responses. No for working/finished/timer/participation.

---

### 17. Live Student Responses — 🟡 Partially Functional

**Implemented.** Any activity that posts `{type: 'lism-activity-response', correct, answer}` to `window.parent` gets forwarded by the join page to `POST /api/join/{code}/response` and broadcast to the teacher instantly. The feed shows student name and answer text, colour-coded by correctness.

**Missing.** The response model has exactly four fields: `correct`, `answer`, `student_id`, `submitted_at`. There is no question ID, no per-question breakdown, no score, no attempt count. So multiple-choice works; the MVP's "coding responses" and "AI conversation responses" have nowhere to go structurally. Critically, **uploaded activities do not report anything** unless the teacher's own HTML happens to implement the undocumented `postMessage` contract — and nothing in the upload UI tells them it exists. In practice this means responses only flow from the canned/AI-generated template.

**Demonstrable now?** Yes with a generated activity. No with a typical teacher-authored upload.

---

### 18. Student Progress Tracking — ❌ Not Implemented

**Implemented.** Only `joined_at`. That is the whole model.

**Missing.** The five states the MVP names — Joined, Working, Finished, Disconnected, Rejoined — do not exist as data or as UI. There is no heartbeat, no presence detection, no per-student WebSocket, no idle timer, no completion flag. A student who closes their laptop is indistinguishable from one who is working.

**Demonstrable now?** No.

---

### 19. WebSocket Updates — 🟡 Partially Functional

**Implemented.** `ConnectionManager` keyed by session code; `/api/ws/session/{code}` accepts connections and broadcasts `student_joined` and `response_submitted` events; dead sockets are pruned on send failure. The teacher's live page connects on mount and appends to state on message. Verified working.

**Missing.** **The WebSocket endpoint has no authentication.** Anyone who knows a 6-character session code — which is printed on a projector — can connect and receive every student name and every answer in real time. Given the code space is only 36⁶, it is also brute-forceable. This is the most serious security finding in the codebase.

Beyond that: no reconnect logic (a dropped socket stays dropped until the teacher refreshes), no heartbeat/ping, only two event types, and the socket is one-directional — the teacher cannot push anything *to* students, which is why remote pause/lock cannot work.

**Demonstrable now?** Yes.

---

### 20. Classroom Controls — 🟡 Partially Functional

**Implemented.** End Session only. `POST /api/sessions/{id}/end` sets status to `ended`; the join page then shows "This session has ended" to anyone arriving afterwards.

**Missing.** Pause, Resume, Lock responses, Unlock responses, Extend timer — five of the six controls in the MVP. None have routes or buttons. They also can't be built on the current WebSocket, which never sends messages toward students. Note too that ending a session does **not** evict students already inside the activity — their iframe keeps running and `POST /api/join/{code}/response` still accepts submissions to an ended session (no status check in `submit_response`).

**Demonstrable now?** End Session only.

---

### 21. Basic Analytics — 🟡 Partially Functional

**Implemented.** Three raw counts on the live page: students joined, response count, and a completion percentage.

**Missing.** Average score, average completion time, question-by-question statistics, and most-common-incorrect-answer — all four of the MVP's analytics items. None are computable from the current schema: responses carry no score and no question ID, and students carry no finish time. No charts library is installed.

**Demonstrable now?** Counts only.

---

### 22. PDF Export — ✅ Fully Functional

**Implemented.** `GET /api/reports/{session_id}/pdf`, teacher-scoped. Uses ReportLab to build a titled document with activity name, session code, join/response counts, and a striped table of every response (student, grade, section, correct, answer truncated to 60 chars). Downloads with a proper filename.

**Missing.** No scores, no completion time, no charts, no analytics section, no AI summary, no teacher notes — all listed in the spec. Answers over 60 characters are silently cut, which will mangle any extended-writing task.

**Demonstrable now?** Yes.

---

### 23. Excel Export — ❌ Not Implemented

**Implemented.** Nothing. `report_service.py` contains `build_csv` and `build_pdf` only. There is no `.xlsx` route and no `openpyxl`/`xlsxwriter` dependency.

**Missing.** The entire feature. (A CSV opens in Excel, but that is not the formatted workbook the spec describes.)

**Demonstrable now?** No.

---

### 24. CSV Export — ✅ Fully Functional

**Implemented.** `GET /api/reports/{session_id}/csv`, teacher-scoped, six columns (Student Name, Grade, Section, Submitted At, Correct, Answer), proper `Content-Disposition` filename.

**Missing.** Same content gaps as the PDF — no score, no duration, no analytics. No BOM, so non-ASCII student names may render wrong when opened directly in Excel.

**Demonstrable now?** Yes.

---

### 25. Session History — 🟡 Partially Functional

**Implemented.** `GET /api/sessions` lists the teacher's sessions newest-first. Shown as "Previous sessions" on the Live Classroom page and as the Reports table (activity, code, status, start time, export buttons). Clicking through re-opens the full live view with all students and responses intact.

**Missing.** No dedicated Session History nav item. No archive action. No search or date filter. No delete. And because storage is in-memory, "history" is only the history since the last backend restart.

**Demonstrable now?** Yes, within a single backend run.

---

### 26. Activity Reuse — 🟡 Partially Functional

**Implemented.** An activity can be launched repeatedly; each launch creates a fresh session with its own code and its own student/response set. This is the core of reuse and it works.

**Missing.** No explicit "reuse" affordance, no way to copy an activity into a new one for editing, and no cross-restart persistence — so reuse next week is not possible today.

**Demonstrable now?** Yes within one backend run.

---

### 27. Duplicate Activity — ❌ Not Implemented

**Implemented.** Nothing. No endpoint, no button.

**Demonstrable now?** No.

---

### 28. Teacher Security / Data Isolation — 🟡 Partially Functional

**Implemented.** Every teacher-facing route depends on `get_current_teacher`, which validates the JWT and loads the teacher. Ownership is then re-checked per resource: `list_activities` and `list_sessions` filter by `teacher_id`; `launch_session`, `get_session`, `end_session` and the report loader all return 404 if `resource.teacher_id != teacher.id`. Teacher A cannot list, open, launch, end or export Teacher B's work. That part is correct.

**Missing / concerns**, in order of severity:

1. **The WebSocket is unauthenticated.** `/api/ws/session/{code}` requires only the session code. Anyone with the code — or brute-forcing the 36⁶ space — streams live student names and answers. (See #19.)
2. **`GET /api/activities/{id}/raw` is unauthenticated and unguessable-by-ID only.** It has to be public for students, but it means any activity's full HTML is readable by anyone holding its ID, with no session check tying the request to a live session.
3. **Response submission is unauthenticated and unvalidated.** `POST /api/join/{code}/response` accepts any `student_id` string. A student can submit answers on a classmate's behalf, or flood the feed. It also doesn't check session status, so responses land after a session ends.
4. **Default JWT secret.** `"dev-secret-change-me"` is used unless `.env` overrides it.
5. **No RBAC.** The spec calls for role-based access control; there is exactly one role. No admin, no `role` column, no permission checks beyond ownership.
6. **No CSRF/CORS review** and no rate limiting on any endpoint.

**Demonstrable now?** Teacher-to-teacher isolation is demonstrable and holds. The unauthenticated surfaces above are real and should not be exposed to a live classroom on a shared network as-is.

---

### 29–31. AI Insights, Activity Library, Settings — ⚪ UI Only / Placeholder

All three are one-line components rendering the shared `ComingSoon` placeholder with a title and a sentence of copy. No routes, no data, no logic behind any of them. They appear in the sidebar and are reachable, so they will look real in a demo — worth knowing before you click them in front of anyone.

**Demonstrable now?** Only as placeholders.

---

## Summary of what is genuinely working end to end

Teacher signs up → generates a stub activity or uploads their own HTML → previews it → launches a session → gets a code, link and QR → students join by name with no account → students answer *an activity that implements the postMessage contract* → the teacher sees joins and answers appear live with no refresh → the teacher ends the session → the teacher exports PDF or CSV. Every step of that chain works today.

## Summary of the largest gaps against the MVP

1. **No persistence.** Everything is lost on restart. This blocks Session History, Activity Reuse and Activity Library from being real features.
2. **No student status model.** Working / Finished / Disconnected / Rejoined don't exist, which is what the Live Classroom Dashboard, progress tracking and most analytics all depend on.
3. **Uploaded activities are silent.** The `postMessage` contract is undocumented and unenforced, so a teacher's own HTML produces zero responses — the platform's central promise ("upload any HTML activity and monitor it") does not hold for uploads today.
4. **The AI generator has no key** and returns an identical stub regardless of input.
5. **Unauthenticated WebSocket** exposes live student data to anyone with the session code.
6. **Missing entirely:** ZIP upload, Prompt Library, Activity Templates, Excel export, duplicate/edit/delete/search on activities, and five of six classroom controls.
