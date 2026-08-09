"""Takes a full backup of the LISM database to a local folder.

The free Supabase tier has no automatic backups and no point-in-time
recovery. Once a term of real marks is in there, "it was deleted and there is
no restore point" is not a sentence anyone wants to say to a head teacher.
This is what stands in for that.

Runs on your own machine, on purpose. The obvious thing would be a scheduled
job in GitHub, but the backup contains real students' names and their written
answers, and a GitHub Actions artifact is downloadable by anyone who can see
the repository. Children's work does not go somewhere it might be public to
save someone a few minutes a month. The connection string stays on your
machine too, rather than being stored as a repository secret.

Usage (from the backend directory, with the virtualenv active):

    python scripts/backup.py

Reads DATABASE_URL from the environment, or falls back to the local database.
Writes a timestamped .zip and keeps the most recent KEEP_BACKUPS of them.

Needs no postgres client tools installed -- it reads through SQLAlchemy, the
same connection the app itself uses.
"""

import csv
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import MetaData, create_engine, select  # noqa: E402

from app.core.config import settings  # noqa: E402

# Kept next to the project rather than inside it, so a backup is never
# committed by accident.
BACKUP_DIR = Path(
    os.getenv("LISM_BACKUP_DIR")
    or Path.home() / "OneDrive" / "Documents" / "LISM Backups"
)
KEEP_BACKUPS = int(os.getenv("LISM_KEEP_BACKUPS", "30"))


def _rows_as_csv(conn, table) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    columns = [c.name for c in table.columns]
    writer.writerow(columns)
    for row in conn.execute(select(table)):
        writer.writerow(["" if v is None else v for v in row])
    return out.getvalue()


def main() -> int:
    url = os.getenv("DATABASE_URL") or settings.database_url
    engine = create_engine(url, pool_pre_ping=True)

    # Host only. Never print the connection string: it carries the password,
    # and this output gets pasted into chats and support tickets.
    from urllib.parse import urlsplit

    host = urlsplit(url).hostname or "(local)"
    print(f"Backing up {host}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    path = BACKUP_DIR / f"lism-backup-{stamp}.zip"

    # Read the database's own shape, not the models'.
    #
    # Selecting the columns the code expects breaks the moment the code is
    # ahead of the database -- which is exactly the situation the startup
    # migration exists to handle, and exactly when a backup matters most. A
    # backup copies what is there.
    metadata = MetaData()
    metadata.reflect(bind=engine)

    counts: dict[str, int] = {}
    with engine.connect() as conn:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for table in metadata.sorted_tables:
                body = _rows_as_csv(conn, table)
                archive.writestr(f"{table.name}.csv", body)
                counts[table.name] = max(0, body.count("\n") - 1)
                print(f"  - {table.name}: {counts[table.name]} rows")

            archive.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "taken_at": datetime.now(timezone.utc).isoformat(),
                        "host": host,
                        "tables": counts,
                        # So a restore knows what shape the data was in.
                        "note": "CSV per table, header row first. Restore with COPY or pandas.",
                    },
                    indent=2,
                ),
            )

    size_kb = path.stat().st_size / 1024
    print(f"\nWrote {path}  ({size_kb:.0f} KB)")

    # A backup nobody checks is not a backup. Say plainly when it looks wrong.
    if counts.get("students", 0) == 0 and counts.get("teachers", 0) == 0:
        print("\nWARNING: no teachers and no students in this backup.")
        print("That usually means DATABASE_URL was not set, so this backed up")
        print("the empty local database instead of the live one.")
        return 1

    old = sorted(BACKUP_DIR.glob("lism-backup-*.zip"))[:-KEEP_BACKUPS]
    for stale in old:
        stale.unlink()
        print(f"Removed old backup {stale.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
