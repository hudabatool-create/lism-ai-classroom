# Deploying LISM AI Classroom

Three separate services, each hosted where it actually fits:

| Piece | Host | Why |
|---|---|---|
| Frontend (Next.js) | **Vercel** | Built for it |
| Backend (FastAPI + WebSockets) | **Railway** | Runs as a real long-lived process — Vercel serverless functions can't hold a WebSocket open or keep a SQLite file on disk |
| Database | **Supabase (Postgres)** | Managed, free tier, survives independently of the backend process |

Local dev keeps working exactly as before (SQLite file, `localhost:3000` ↔ `localhost:8000`) — nothing here changes that. Every value that differs between local and production is an environment variable; no code changes are needed to go from one to the other.

## 0. Push this repo to GitHub

Both Railway and Vercel deploy by connecting to a GitHub repo.

```bash
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin master
```

(Create the empty repo on github.com first if you haven't — `gh repo create` works too if you have the GitHub CLI.)

## 1. Supabase — production database

1. Go to [supabase.com](https://supabase.com), create a free project.
2. In the project dashboard: **Project Settings → Database → Connection string** — copy the **URI** under "Connection pooling" or the direct connection. For this app's traffic (a school, not internet-scale), the **direct connection** (port 5432) is simplest:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
3. Keep this URL private — it's the `DATABASE_URL` for Railway below. You do **not** need to run the SQL in `backend/db/supabase_schema.sql` — that file is stale; the actual schema is created automatically by SQLAlchemy on first startup (`Base.metadata.create_all`), against whatever `DATABASE_URL` points at.

## 2. Railway — backend

1. [railway.app](https://railway.app) → New Project → **Deploy from GitHub repo** → select this repo.
2. In the service's **Settings**, set **Root Directory** to `backend`.
3. Railway auto-detects Python and uses `backend/Procfile` (`web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`) as the start command, and `backend/.python-version` to pin Python 3.12.
4. In **Variables**, set:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the Supabase connection string from step 1 |
   | `JWT_SECRET` | a real random value — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `JWT_ALGORITHM` | `HS256` |
   | `JWT_EXPIRE_MINUTES` | `10080` |
   | `COOKIE_SECURE` | `true` |
   | `COOKIE_SAMESITE` | `none` |
   | `FRONTEND_ORIGIN` | your Vercel URL (you'll fill this in after step 3 — use a placeholder like `https://placeholder.vercel.app` for now, come back and update it) |
   | `OPENAI_API_KEY` | optional, only if you want real AI generation instead of the canned template |
   | `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` | optional, only if you want real verification/reset emails instead of them being logged |

5. Deploy. Once it's live, note the public URL Railway gives you (Settings → Networking → Generate Domain if it's not already public), e.g. `https://your-app.up.railway.app`.
6. Sanity check: `curl https://your-app.up.railway.app/api/health` should return `{"status":"ok",...}`.

## 3. Vercel — frontend

1. [vercel.com](https://vercel.com) → Add New Project → import the same GitHub repo.
2. Set **Root Directory** to `frontend`. Vercel auto-detects Next.js.
3. In **Environment Variables**, set:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | the Railway URL from step 2, e.g. `https://your-app.up.railway.app` |

4. Deploy. Note the resulting URL, e.g. `https://your-app.vercel.app`.

## 4. Close the loop

Go back to Railway and update `FRONTEND_ORIGIN` to the real Vercel URL from step 3 (exact origin, no trailing slash). Railway redeploys automatically on a variable change. This value is used for both CORS (so the browser is allowed to call the API at all) and for the join links/QR codes students actually see, so it has to be correct.

### Adding a custom domain

**Update `FRONTEND_ORIGIN` the moment you point a new domain at the app**, or logging in from it will fail. The browser blocks the request before it reaches any route, so Railway's logs stay clean while the whole app appears broken — there is nothing to find on the server side.

`FRONTEND_ORIGIN` accepts a comma-separated list, and the **first entry is canonical**: it is what goes into student join links, QR codes and verification emails. Put the domain you want people to see first.

```
FRONTEND_ORIGIN=https://lismaiclass.com,https://www.lismaiclass.com,https://lism-ai-classroom.vercel.app
```

Keeping the old `.vercel.app` origin in the list means links already shared with students keep working. Note that adding a custom domain in Vercel can move the production deployment off the `.vercel.app` alias entirely — if that address starts returning `DEPLOYMENT_NOT_FOUND`, the app has not gone down, it has moved.

To check CORS from a new domain without opening a browser:

```bash
curl -s -D - -o /dev/null -X OPTIONS -H "Origin: https://YOUR-DOMAIN" -H "Access-Control-Request-Method: POST" https://YOUR-BACKEND/api/auth/login | grep -i "access-control-allow-origin"
```

An allowed origin echoes back in that header. No header means the browser will refuse the request.

## 5. Smoke test

1. Open the Vercel URL, sign up a teacher account.
2. Generate or upload an activity, launch a session.
3. Open the join link in a private/incognito window, join as a student.
4. Confirm the teacher dashboard shows the student live (this exercises the cross-origin WebSocket + cookie path, the part most likely to misbehave if `COOKIE_SAMESITE`/`COOKIE_SECURE` are wrong — a login that silently "fails" with no error, or a dashboard that never updates live, usually means one of those two is misconfigured).

## Known constraints at this scale

- **Single Railway instance**: writes are currently serialized through one in-process lock (see the concurrency test results from this session) — correct under real load, but only tested up to ~45 concurrent students across 2 parallel classrooms. Fine for one school; revisit if you scale to many schools running simultaneously.
- **login lockout counters are in-memory**: they reset if Railway restarts/redeploys the instance. Not a security-critical loss, just noted for completeness.
- **No migration framework yet** (Alembic): schema changes to the SQLAlchemy models will need a manual migration once there's real production data worth preserving carefully. Fine today since `create_all` only ever adds tables that don't exist yet.
