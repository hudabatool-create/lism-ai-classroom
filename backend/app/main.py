from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import activities, auth, coach, insights, prompts, reports, sessions, stages
from app.core.config import settings
from app.db import models  # noqa: F401 -- registers tables on Base.metadata
from app.db.base import Base, engine

app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def _create_tables():
    # No migration framework yet (Alembic) -- fine for a scaffold whose
    # schema isn't expected to change out from under real data yet. Add one
    # before this app has production data worth migrating carefully.
    Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
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
