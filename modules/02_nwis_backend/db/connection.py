"""
Environment-driven connection to the canonical PostgreSQL/PostGIS database
(database/schema.sql). No secrets in source — the DSN comes entirely from
environment variables, read once at import time.

Two ways to configure it, checked in this order:
  1. NWIS_DATABASE_URL — a full psycopg-style DSN or libpq URL, e.g.
     "postgresql://nwis:nwis_dev_password@localhost:5433/nwis"
  2. The individual NWIS_DB_* variables below, assembled into a DSN —
     convenient for matching database/docker-compose.yml's defaults
     without having to hand-assemble a URL.

If neither is set, `get_pool()` raises NWISDatabaseNotConfigured rather
than silently returning None or falling back to some hidden default — a
caller (server.py) uses that to decide whether to route a request through
the database-backed repository layer or the existing in-memory store, and
a misconfigured deployment should fail loudly instead of pretending it's
degraded.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from loguru import logger

try:
    import psycopg
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover — psycopg[binary]/psycopg_pool not installed
    psycopg = None
    ConnectionPool = None


class NWISDatabaseNotConfigured(RuntimeError):
    """Raised when DB-backed access is attempted but no DSN is configured."""


class NWISDatabaseUnavailable(RuntimeError):
    """Raised when a DSN is configured but the database cannot actually be
    reached — kept distinct from NWISDatabaseNotConfigured so a caller (and
    an operator reading logs) can tell "not set up for this" apart from
    "set up but currently down"."""


def _build_dsn() -> Optional[str]:
    explicit = os.environ.get("NWIS_DATABASE_URL")
    if explicit:
        return explicit

    host = os.environ.get("NWIS_DB_HOST")
    if not host:
        return None  # no DB configuration at all — stay on the in-memory store

    port = os.environ.get("NWIS_DB_PORT", "5433")  # matches docker-compose.yml's host port
    dbname = os.environ.get("NWIS_DB_NAME", "nwis")
    user = os.environ.get("NWIS_DB_USER", "nwis")
    password = os.environ.get("NWIS_DB_PASSWORD", "")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


_DSN = _build_dsn()
_pool: Optional["ConnectionPool"] = None


def is_configured() -> bool:
    return _DSN is not None


def get_pool() -> "ConnectionPool":
    """Lazily create (once) and return the process-wide connection pool.

    Raises NWISDatabaseNotConfigured if no DSN is set, or
    NWISDatabaseUnavailable if psycopg itself isn't installed. Does NOT
    eagerly connect at import time — that would make importing this module
    fail the whole server process if the DB happens to be down, for a
    feature (the migrated vertical slice) that is opt-in.
    """
    global _pool
    if _DSN is None:
        raise NWISDatabaseNotConfigured(
            "No database configured. Set NWIS_DATABASE_URL (or NWIS_DB_HOST "
            "+ NWIS_DB_NAME/NWIS_DB_USER/NWIS_DB_PASSWORD) to enable the "
            "PostgreSQL-backed well/nearby-wells path. Falling back to the "
            "in-memory NWISDataStore until then."
        )
    if psycopg is None or ConnectionPool is None:
        raise NWISDatabaseUnavailable(
            "NWIS_DATABASE_URL is set but psycopg[binary]/psycopg_pool is not "
            "installed. Run: pip install -r database/requirements.txt"
        )
    if _pool is None:
        logger.info("Opening NWIS database connection pool...")
        try:
            _pool = ConnectionPool(_DSN, min_size=1, max_size=10, open=True, timeout=5.0)
        except Exception as exc:
            raise NWISDatabaseUnavailable(f"Could not open database connection pool: {exc}") from exc
        logger.success("NWIS database connection pool open")
    return _pool


def close_pool() -> bool:
    """Close the process-wide connection pool if one was ever opened.
    Called from the unified backend's shutdown so pooled connections are
    released deterministically instead of at interpreter teardown. Safe to
    call when no pool exists (returns False) and safe to call twice."""
    global _pool
    pool, _pool = _pool, None
    if pool is None:
        return False
    pool.close()
    return True


@contextmanager
def get_connection() -> Iterator["psycopg.Connection"]:
    """Checkout a pooled connection for the duration of a `with` block."""
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


def healthcheck() -> dict:
    """Used by GET /api/v2/health — never raises; reports status instead.

    The "error" field (Pass 2 hardening) is the exception's CLASS NAME only,
    not str(exc) — psycopg's connection-failure messages include host/port/
    user (confirmed not the password, but still internal connection detail
    that shouldn't sit in a client-facing JSON body). Full detail is always
    in the server log line below; this function's return value is what a
    caller actually sees.
    """
    if not is_configured():
        return {"configured": False, "reachable": None}
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"configured": True, "reachable": True}
    except Exception as exc:
        logger.warning(f"Database healthcheck failed: {exc}")
        return {"configured": True, "reachable": False, "error": type(exc).__name__}
