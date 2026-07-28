from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import activities, auth, coach, insights, prompts, reports, sessions, stages
from app.core.config import settings
from app.db import models  # noqa: F401 -- registers tables on Base.metadata
from app.db.base import Base, engine
from app.db.migrate import add_missing_columns

app = FastAPI(title=settings.app_name)


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
    return {"status": "ok", "app": settings.app_name}
