import sqlite3
from datetime import datetime, timezone
from typing import List

from .models import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    url         TEXT PRIMARY KEY,
    title       TEXT,
    company     TEXT,
    location    TEXT,
    source      TEXT,
    interface   TEXT,
    sponsorship TEXT,
    first_seen  TEXT
)
"""


class JobDB:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def filter_new(self, jobs: List[Job]) -> List[Job]:
        """Insert jobs, returning only the ones not seen in any previous run."""
        now = datetime.now(timezone.utc).isoformat()
        new_jobs = []
        for job in jobs:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO jobs "
                "(url, title, company, location, source, interface, sponsorship, first_seen) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (job.url, job.title, job.company, job.location,
                 job.source, job.interface, job.sponsorship, now),
            )
            if cur.rowcount == 1:
                new_jobs.append(job)
        self.conn.commit()
        return new_jobs

    def close(self):
        self.conn.close()
