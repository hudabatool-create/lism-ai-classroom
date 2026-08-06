import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import activities, auth, coach, insights, prompts, reports, sessions, stages
from app.core.config import settings
from app.db import models  # noqa: F401 -- registers tables on Base.metadata
from app.db.base import Base, engine
from app.db.migrate import add_missing_columns

app = FastAPI(title=settings.app_name)

# Railway sets this on every deploy; empty locally.
_COMMIT = (os.getenv("RAILWAY_GIT_COMMIT_SHA") or "local")[:8]


@app.on_event("startup")
def _create_tables():
    # create_all adds missing tables; add_missing_columns adds columns that
    # exist on the models but not yet in an already-deployed database, which
    # create_all will not do. Both are additive and safe to re-run. See
    # app/db/migrate.py for why this is a stopgap rather than Alembic.
    Base.metadata.create_all(bind=engine)
    add_missing_columns()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def no_store(request, call_next):
    """Nothing this API returns is safe to cache.

    Every response describes right now -- which stage is running, who has
    joined, what has been answered. Sending no cache headers left browsers to
    guess, and they guessed wrong: a student's page polled for the current
    stage and was handed the same stale "nothing running" answer from cache
    for the whole lesson, so the screen never left "Waiting for your teacher".
    Rejoining fixed it only because that is a POST, which is never cached.
    """
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


app.include_router(auth.router)
app.include_router(activities.router)
app.include_router(sessions.router)
app.include_router(stages.router)
app.include_router(coach.router)
app.include_router(insights.router)
app.include_router(prompts.router)
app.include_router(reports.router)


@app.get("/api/health")
def health():
    """Liveness, plus the two settings that break the app invisibly when wrong.

    A misconfigured origin fails in the browser before the request reaches any
    route, so the server logs stay clean while the whole app appears broken --
    there is genuinely nothing to find server-side. Reporting what the running
    container actually holds turns that from guesswork into one request.

    These are public URLs and public cookie flags, not secrets. No credential,
    key or connection string is exposed here, and nothing else about the
    environment is.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        # Which build is actually serving. Without this, "did my fix deploy?"
        # can only be answered by inference, which cost hours on this project.
        "commit": _COMMIT,
        "frontend_origins": settings.frontend_origins,
        "canonical_origin": settings.canonical_origin,
        "cookie_samesite": settings.cookie_samesite,
        "cookie_secure": settings.cookie_secure,
    }


@app.get("/api/health/db")
def health_db():
    """Round-trip time to the database, measured from inside the container.

    A classroom's speed is dominated by this number: every join and every
    answer costs at least one of these. If it is tens of milliseconds the app
    is the bottleneck; if it is hundreds, the database's region is.
    """
    import time

    from sqlalchemy import text

    from app.db.base import engine

    from urllib.parse import urlsplit

    # Surface the reason a connection failed rather than a bare 500. Under
    # burst this is the difference between "the pool is exhausted" and "the
    # database refused us", which need opposite fixes.
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        connect_error = None
    except Exception as exc:
        connect_error = f"{type(exc).__name__}: {exc}"[:300]

    samples = []
    for _ in range(5):
        t0 = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        samples.append(round((time.perf_counter() - t0) * 1000, 1))
    pool = engine.pool

    # Host only -- never the user or password. Enough to see which database
    # the running container is actually talking to, which is the question
    # that matters when a DATABASE_URL change appears not to have landed.
    parts = urlsplit(settings.database_url)
    host = parts.hostname or "(none)"
    region = next((r for r in ("ap-southeast-1", "ap-south-1", "eu-central-1",
                               "us-east-1", "us-west-1") if r in host), "unknown")

    return {
        "db_host": host,
        "db_region": region,
        "connect_error": connect_error,
        # Where this container runs. The database needs to be near THIS, not
        # near the school: users pay one round trip to reach the app, but the
        # app pays one to the database for every query in the request.
        "app_region": os.getenv("RAILWAY_REPLICA_REGION") or os.getenv("RAILWAY_REGION") or "unknown",
        "round_trip_ms": samples,
        "median_ms": sorted(samples)[len(samples) // 2],
        "pool_size": getattr(pool, "size", lambda: None)(),
        "checked_out": getattr(pool, "checkedout", lambda: None)(),
        "overflow": getattr(pool, "overflow", lambda: None)(),
    }
