"""
NWIS Module 01 — Persistent Job Store

The original implementation kept job status in a plain Python dict, which
means every ingestion job (and its progress/result linkage) evaporates on
server restart, crash, or `--reload` triggering a process respawn — exactly
the kind of thing that happens in "process any document in real time"
production use. This module swaps that for a SQLite-backed store so job
status survives restarts, while keeping a simple, dict-like API.

Not a distributed queue: this is a single-file, single-process store. If
this ever needs to scale horizontally (multiple API instances behind a load
balancer), swap it for Redis/Postgres — but for a single-instance air-gapped
deployment (this system's actual target), SQLite gives real durability with
zero extra infrastructure to stand up.
"""

from __future__ import annotations
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "jobs.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _serialize(value: dict) -> str:
    # default=str handles enums (IngestJobStatus is a str-Enum so this is
    # mostly a no-op) and any datetime objects that slip in.
    return json.dumps(value, default=str)


class SQLiteJobStore:
    """Dict-like, thread-safe, disk-persisted job status store."""

    def __init__(self, db_path: Path = DB_PATH):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    # -- internal, lock must already be held -------------------------------
    def _select_nolock(self, job_id: str) -> Optional[dict]:
        cur = self._conn.execute("SELECT data FROM jobs WHERE job_id = ?", (job_id,))
        row = cur.fetchone()
        return json.loads(row[0]) if row else None

    def _write_nolock(self, job_id: str, value: dict) -> None:
        self._conn.execute(
            "INSERT INTO jobs (job_id, data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(job_id) DO UPDATE SET data=excluded.data, updated_at=CURRENT_TIMESTAMP",
            (job_id, _serialize(value)),
        )
        self._conn.commit()

    # -- public API ---------------------------------------------------------
    def create(self, job_id: str, initial: dict) -> None:
        """Insert a brand-new job record (overwrites if job_id already exists)."""
        with self._lock:
            self._write_nolock(job_id, dict(initial))

    def update(self, job_id: str, **fields: Any) -> None:
        """Merge `fields` into an existing job record (read-modify-write)."""
        with self._lock:
            current = self._select_nolock(job_id) or {"job_id": job_id}
            current.update(fields)
            self._write_nolock(job_id, current)

    def get(self, job_id: str, default: Optional[dict] = None) -> Optional[dict]:
        with self._lock:
            return self._select_nolock(job_id) or default

    def __contains__(self, job_id: str) -> bool:
        return self.get(job_id) is not None

    def __len__(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM jobs")
            return cur.fetchone()[0]

    def values(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute("SELECT data FROM jobs ORDER BY updated_at DESC")
            rows = cur.fetchall()
        return [json.loads(r[0]) for r in rows]

    def prune_older_than(self, days: int = 7) -> int:
        """Housekeeping: delete job records older than N days. Returns count removed."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM jobs WHERE updated_at < datetime('now', ?)",
                (f"-{days} days",),
            )
            self._conn.commit()
            return cur.rowcount
