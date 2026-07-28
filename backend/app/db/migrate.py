"""Adds columns that exist on the models but not yet in the database.

`Base.metadata.create_all()` creates missing *tables* and silently ignores
tables that already exist -- it never adds a column. So shipping a new model
field to an already-deployed database leaves every query selecting a column
that isn't there, and the app fails at runtime rather than at startup.

This is a deliberate stopgap, not a migration framework. It only ever runs
`ALTER TABLE ... ADD COLUMN`, which is safe and non-destructive on both
SQLite and Postgres: it never drops, renames, retypes or reorders anything,
and it skips any column that already exists, so it is safe to run on every
boot. Anything beyond adding a nullable/defaulted column -- renames, type
changes, backfills, dropping columns -- needs Alembic, and that is the point
to introduce it.
"""

import logging

from sqlalchemy import inspect, text

from app.db.base import Base, engine

logger = logging.getLogger("lism.migrate")

# SQLAlchemy type -> portable DDL understood by both SQLite and Postgres.
_DDL_TYPES = {
    "BOOLEAN": "BOOLEAN",
    "INTEGER": "INTEGER",
    "VARCHAR": "VARCHAR",
    "TEXT": "TEXT",
    "FLOAT": "FLOAT",
    "DATETIME": "TIMESTAMP",
}


def _column_ddl_type(column) -> str:
    compiled = str(column.type).split("(")[0].upper()
    return _DDL_TYPES.get(compiled, "TEXT")


def _default_clause(column) -> str:
    default = getattr(column, "default", None)
    if default is None or default.arg is None or callable(default.arg):
        return ""
    value = default.arg
    if isinstance(value, bool):
        return f" DEFAULT {'TRUE' if value else 'FALSE'}"
    if isinstance(value, (int, float)):
        return f" DEFAULT {value}"
    return f" DEFAULT '{value}'"


def add_missing_columns() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # create_all just made it, with every column
        present = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            ddl = (
                f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" '
                f"{_column_ddl_type(column)}{_default_clause(column)}"
            )
            with engine.begin() as conn:
                conn.execute(text(ddl))
            logger.warning("Added missing column %s.%s", table.name, column.name)

    _ensure_student_name_key()


def _ensure_student_name_key() -> None:
    """Backfill students.name_key and enforce one participant per name.

    The uniqueness used to be maintained by a process-wide lock around the
    find-or-create, which serialised every write in the app and made a class
    of thirty joining at once take minutes. The database can enforce it for
    free and in parallel -- this puts the guarantee where it belongs.

    Backfill first, then index: creating the index on unbackfilled rows would
    collide every NULL on SQLite.
    """
    from app.services.data_store import _normalize_name

    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, name FROM students WHERE name_key IS NULL")).fetchall()
        for row in rows:
            conn.execute(
                text("UPDATE students SET name_key = :k WHERE id = :i"),
                {"k": _normalize_name(row.name), "i": row.id},
            )
        if rows:
            logger.warning("Backfilled name_key for %d students", len(rows))

    try:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_students_session_name_key "
                "ON students (session_id, name_key)"
            ))
    except Exception as exc:
        # Historic duplicates (created before this constraint existed) block
        # the index. The find-or-create still works without it -- it just
        # falls back to losing a rare race rather than being prevented from
        # one -- so this must never stop the app booting.
        logger.warning("Could not create unique student index (existing duplicates?): %s", exc)
