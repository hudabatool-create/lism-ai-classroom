# Master prompts

**`backend/app/prompts/*.txt` are the live files.** They are served to teachers
through the Prompt Library (`backend/app/api/routes/prompts.py`) and read by
`ai_service.py`; nothing else is loaded. Any copies elsewhere are for reading
and review only.

Teachers do not generate activities inside LISM. They copy a prompt from the
Prompt Library, run it in ChatGPT / Claude / Gemini, and upload the resulting
HTML. The **Create an Activity** page walks through that. Because every prompt
below carries the LISM manifest, the uploaded activity arrives teacher-paced.

## Full lesson frameworks

| Live file | Version |
|---|---|
| `lesson_deck_master_prompt.txt` | Interactive Lesson Deck v10 |
| `worksheet_master_prompt.txt` | Interactive Worksheet v8 |

These keep the full ALL/MOST/SOME + DOK 1–4 framework ending in a single final
Challenge/Extension Task.

## Single-purpose activities

| Live file | Prompt Library title | Stages |
|---|---|---|
| `starter_prompt.txt` | Starter / Retrieval Activity | 3 |
| `poll_prompt.txt` | Poll / Exit Ticket | 4 |
| `quiz_prompt.txt` | Quiz | 9 |
| `mcq_prompt.txt` | Multiple Choice Questions | 5 |
| `true_false_prompt.txt` | True / False with Justification | 6 |
| `matching_prompt.txt` | Matching Activity | 2 |
| `drag_drop_prompt.txt` | Drag & Drop Activity | 3 |
| `flashcards_prompt.txt` | Flashcards | 9 |
| `crossword_prompt.txt` | Crossword | 3 |
| `brainstorm_prompt.txt` | Brainstorm Board | 4 |
| `game_prompt.txt` | Learning Game | 4 |
| `escape_room_prompt.txt` | Escape Room | 5 |
| `simulation_prompt.txt` | Simulation | 5 |
| `coding_challenge_prompt.txt` | Coding Challenge | 6 |

Each has the structure that activity type actually needs rather than a lesson
skeleton — a flashcard set is one stage per card, a quiz one per question, an
escape room one per lock. All of them cover every subject, including Arabic
(RTL layout, tashkeel/tatweel normalisation, Arabic-Indic digits).

## Editing

Edit the file under `backend/app/prompts/`. Editing a copy elsewhere changes
nothing. (That exact mistake once left the generator running v3/v1 while
revised prompts sat unused in a docs folder.) When adding a new prompt, also
register it in `_BUILTIN_PROMPTS` — and keep any version number in the title
matching the file, since a stale title is what makes a teacher think they have
the wrong prompt.

Two blocks are appended automatically by `ai_service.py` when a prompt does not
already contain them, so avoid duplicating them by hand:

- `PEDAGOGY_REQUIREMENTS` — bans vague filler questions, requires content
  specific to the topic and plausible distractors.
- `LISM_INTEGRATION_ADDENDUM` — the manifest, the command/event contract, and
  the preview rules. See `docs/LISM_ACTIVITY_CONTRACT.md` for the full
  specification that both sides implement.

## When the manifest goes missing

An outside AI sometimes drops the manifest block. `manifest_service.py` then
recovers stages from the activity's own section markers and headings, which is
why its patterns cover the section names these prompts produce — "Card 3",
"Question 5", "Lock 2", "Scenario", "Test Cases". Adding a prompt with new
section names means adding those names to `_STAGE_PATTERNS` too, or an upload
without a manifest collapses into one unnamed stage.
