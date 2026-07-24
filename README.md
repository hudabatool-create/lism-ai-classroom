# LISM AI Classroom

Create. Engage. Monitor. Analyze. Inspire.

A teacher-facing platform for launching interactive HTML classroom activities, monitoring student responses live, and exporting reports — without any hosting, deployment, or coding knowledge required from the teacher.

This repo is an initial scaffold: a fully working end-to-end vertical slice (login → create/upload an activity → launch a session → students join via QR/link → live responses → export a report), plus placeholder pages for the sections of the product spec that need real persistence or AI design work before they're built out (AI Insights, Activity Library, Settings).

## Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Backend**: FastAPI (Python), native WebSockets for live updates
- **Data**: in-memory store today (`backend/app/services/data_store.py`); `backend/db/supabase_schema.sql` has the real Postgres schema for when this moves to Supabase
- **AI**: OpenAI if `OPENAI_API_KEY` is set, otherwise a canned interactive HTML template so the generator flow works with zero config

## Prerequisites

Neither of these was found on this machine when the scaffold was created — install them before running the app:

- **Python 3.11+** — https://www.python.org/downloads/ (check "Add python.exe to PATH" during install)
- **Node.js 20+** (includes npm) — https://nodejs.org/

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Runs on http://localhost:8000. Interactive API docs at http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Runs on http://localhost:3000.

## What's real vs. mocked in this scaffold

| Feature | Status |
|---|---|
| Teacher signup / login | Real (JWT issued by the backend against an in-memory teacher store) |
| Upload HTML activity | Real (file is stored and served back by the backend) |
| Generate activity with AI | Real flow; uses OpenAI if `OPENAI_API_KEY` is set, otherwise a canned template |
| Launch session, QR code, join link | Real |
| Student join + live responses (WebSocket) | Real |
| Reports (PDF/CSV export) | Real |
| AI Insights, Activity Library, Settings | Placeholder — need real data volume / persistence first |
| Supabase persistence | Not yet wired — see `db/supabase_schema.sql` and swap `data_store.py` |

## Going live with real Supabase + OpenAI

1. Create a Supabase project, run `backend/db/supabase_schema.sql` against it.
2. Fill in `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` in `backend/.env`.
3. Reimplement `backend/app/services/data_store.py` against Supabase (same method signatures — routes don't need to change).
4. Set `OPENAI_API_KEY` in `backend/.env` to enable real AI-generated activities.
5. Set `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `frontend/.env.local` if you move auth to Supabase directly.

## Project structure

```
lismclass/
  backend/
    app/
      core/       config, JWT auth
      api/routes/ auth, activities, sessions (live + WebSocket), reports
      services/   data store, AI generation, WebSocket manager, PDF/CSV export
    db/           future Supabase schema
  frontend/
    src/
      app/        Next.js App Router pages (auth, dashboard, public join page)
      components/ Sidebar, AuthGuard, StatCard, ComingSoon
      lib/        API client, shared types
```
