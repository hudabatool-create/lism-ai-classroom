"""Who has actually used LISM, and what did they do?

Answers the question a pilot lives or dies by: has anyone other than me tried
this? Signups on their own do not answer it -- an account created and never
used is not a teacher who tried the platform. A session launched with students
in it is.

Runs on your own machine against your own database. There is deliberately no
API endpoint for this: a teacher list is not something a public API should be
able to hand out, however convenient it would be.

Usage (from the backend directory):

    python scripts/usage.py

Reads DATABASE_URL from the environment, or the local database if unset.
"""

import os
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import MetaData, create_engine, select  # noqa: E402

from app.core.config import settings  # noqa: E402

# Accounts created by load tests and browser checks during development. Real
# teachers do not have example.com addresses, and every generated account was
# prefixed zz- for exactly this reason.
def _is_test_account(email: str) -> bool:
    email = (email or "").lower()
    return email.endswith("@example.com") or email.startswith("zz-")


def main() -> int:
    url = os.getenv("DATABASE_URL") or settings.database_url
    engine = create_engine(url, pool_pre_ping=True)
    print(f"Reading {urlsplit(url).hostname or '(local)'}\n")

    meta = MetaData()
    meta.reflect(bind=engine)
    teachers_t = meta.tables.get("teachers")
    sessions_t = meta.tables.get("sessions")
    students_t = meta.tables.get("students")
    responses_t = meta.tables.get("responses")
    activities_t = meta.tables.get("activities")
    if teachers_t is None:
        print("No teachers table -- is DATABASE_URL pointing at the right database?")
        return 1

    with engine.connect() as conn:
        teachers = [dict(r._mapping) for r in conn.execute(select(teachers_t))]
        sessions = [dict(r._mapping) for r in conn.execute(select(sessions_t))] if sessions_t is not None else []
        students = [dict(r._mapping) for r in conn.execute(select(students_t))] if students_t is not None else []
        responses = [dict(r._mapping) for r in conn.execute(select(responses_t))] if responses_t is not None else []
        activities = [dict(r._mapping) for r in conn.execute(select(activities_t))] if activities_t is not None else []

    real = [t for t in teachers if not _is_test_account(t.get("email", ""))]
    test = len(teachers) - len(real)

    students_by_session = defaultdict(int)
    for s in students:
        students_by_session[s.get("session_id")] += 1
    responses_by_session = defaultdict(int)
    for r in responses:
        responses_by_session[r.get("session_id")] += 1
    activities_by_teacher = defaultdict(int)
    for a in activities:
        activities_by_teacher[a.get("teacher_id")] += 1

    print(f"ACCOUNTS: {len(real)} real, {test} test accounts ignored\n")

    for t in sorted(real, key=lambda x: str(x.get("created_at") or "")):
        mine = [s for s in sessions if s.get("teacher_id") == t["id"]]
        joined = sum(students_by_session[s["id"]] for s in mine)
        answers = sum(responses_by_session[s["id"]] for s in mine)
        # A session with students in it is someone actually trying it. One with
        # nobody is a teacher who opened the page and stopped.
        with_students = [s for s in mine if students_by_session[s["id"]] > 0]

        print(f"  {t.get('name', '?')}  <{t.get('email', '?')}>")
        print(f"      signed up   : {str(t.get('created_at'))[:16]}")
        print(f"      verified    : {t.get('email_verified')}")
        print(f"      activities  : {activities_by_teacher[t['id']]}")
        print(f"      sessions    : {len(mine)} launched, {len(with_students)} with students")
        print(f"      students    : {joined} joined,  {answers} answers submitted")
        if with_students:
            last = max(with_students, key=lambda s: str(s.get("created_at") or ""))
            print(f"      last used   : {str(last.get('created_at'))[:16]}")
        print()

    others = [t for t in real if not str(t.get("email", "")).lower().startswith("hudasulman")]
    tried = [
        t for t in others
        if any(students_by_session[s["id"]] > 0 for s in sessions if s.get("teacher_id") == t["id"])
    ]

    print("-" * 60)
    print(f"Other people with accounts      : {len(others)}")
    print(f"Of those, who ran a real session: {len(tried)}")
    if tried:
        for t in tried:
            print(f"    - {t.get('name')} <{t.get('email')}>")
    else:
        print("    (nobody else has run a session with students in it yet)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
