# Master prompts

**`backend/app/prompts/*.txt` are the live files.** `ai_service.py` reads them
at generation time; nothing else is loaded. The copies here are for reading and
review only.

| Live file (used by the generator) | Version |
|---|---|
| `backend/app/prompts/lesson_deck_master_prompt.txt` | Interactive Lesson Deck v10 |
| `backend/app/prompts/worksheet_master_prompt.txt` | Interactive Worksheet v8 |

To update a prompt, edit the file under `backend/app/prompts/` — editing only a
copy here changes nothing about what gets generated. (That exact mistake once
left the generator running v3/v1 while revised prompts sat unused in this
folder.)

Two things are appended to every prompt automatically by `ai_service.py`, so
they must NOT be duplicated in the prompt text itself:

- `PEDAGOGY_REQUIREMENTS` — bans vague filler questions, requires content
  specific to the topic and plausible distractors.
- `LISM_INTEGRATION_ADDENDUM` — the manifest, the command/event contract, and
  the preview rules. See `docs/LISM_ACTIVITY_CONTRACT.md` for the full
  specification that both sides implement.
