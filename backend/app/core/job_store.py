"""
NWIS Persistent Job Store
SQLite-backed thread-safe store for document ingestion & background processing tasks.
"""

from __future__ import annotations
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional
from app.config import settings


def _serialize(value: dict) -> str:
    return json.dumps(value, default=str)


class SQLiteJobStore:
    """Dict-like, thread-safe, disk-persisted job status store."""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or settings.SQLITE_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
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

    def create(self, job_id: str, initial: dict) -> None:
        with self._lock:
            self._write_nolock(job_id, dict(initial))

    def update(self, job_id: str, **fields: Any) -> None:
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
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM jobs WHERE updated_at < datetime('now', ?)",
                (f"-{days} days",),
            )
            self._conn.commit()
            return cur.rowcount
