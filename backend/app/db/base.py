"""Engine/session setup. SQLite by default (DATABASE_URL unset) so the app
persists with zero external setup; any Postgres URL (Supabase or otherwise)
works unchanged for public deployment -- nothing here is SQLite-specific
except the two pragmas below, which no-op on other backends.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

# Pool sizing matters now that requests actually run in parallel. While a
# single lock serialised every write, one connection was enough and these
# settings would have changed nothing; without it, a class of thirty pressing
# Join together needs real concurrency.
#
# pool_pre_ping costs one cheap round trip per checkout and saves the
# "server closed the connection unexpectedly" failure that hits any pooled
# app whose database or proxy times out idle connections -- which is exactly
# what a classroom does between lessons.
_pool_options = {} if _is_sqlite else {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_pre_ping": True,
    "pool_recycle": 1800,
    "pool_timeout": 30,
}

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    **_pool_options,
)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        # WAL lets readers and a writer proceed concurrently instead of
        # locking the whole file -- this app opens a short-lived session per
        # store call, often from multiple threadpool threads at once.
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
