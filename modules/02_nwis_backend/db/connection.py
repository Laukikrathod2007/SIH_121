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
import re
from contextlib import contextmanager
from typing import Iterator, Optional

from loguru import logger

try:
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover — psycopg[binary]/psycopg_pool not installed
    psycopg = None
    conninfo_to_dict = None
    ConnectionPool = None


class NWISDatabaseNotConfigured(RuntimeError):
    """Raised when DB-backed access is attempted but no DSN is configured."""


class NWISDatabaseUnavailable(RuntimeError):
    """Raised when a DSN is configured but the database cannot actually be
    reached — kept distinct from NWISDatabaseNotConfigured so a caller (and
    an operator reading logs) can tell "not set up for this" apart from
    "set up but currently down"."""


class NWISDatabaseMisconfigured(RuntimeError):
    """Raised when NWIS_DATABASE_URL is set but malformed in a way that
    would silently corrupt the connection (e.g. embedded whitespace/control
    characters that psycopg's parser folds into the last field instead of
    rejecting) — kept distinct from NWISDatabaseUnavailable because this is
    a configuration bug the operator must fix, not a transient network/DB
    outage a retry would resolve.

    Root cause this guards against (confirmed live on a real deploy): a
    dashboard environment-variable field (e.g. Render's) can introduce a
    trailing newline when a secret is pasted/saved. psycopg's own
    conninfo parser does NOT reject this -- it silently appends the
    newline onto whatever field comes last in the DSN (typically dbname),
    so `.../postgres\n` connects to a database literally named
    `"postgres\n"`, which of course doesn't exist. The resulting error
    (`FATAL: database "postgres\n" does not exist`) looks like a wrong
    database name, not a whitespace bug, unless you go looking for it --
    confirmed by reproducing this exact error locally with a synthetic
    trailing newline before writing this check.
    """


# Control characters (newline, carriage return, tab, etc.) anywhere in a
# raw DSN mean something upstream corrupted the value -- a dashboard paste,
# a stray trailing newline from a shell/file, or similar. A legitimate
# connection string has none of these (certainly not in a plain
# postgresql://... URL, and the `host=... key=value` form used by the
# NWIS_DB_* fallback below doesn't produce them either since each piece is
# read individually).
_CONTROL_CHARS_RE = re.compile(r"[\r\n\t\x00-\x08\x0b\x0c\x0e-\x1f]")


def _sanitize_dsn_env_value(raw: str) -> str:
    """Strips ONLY leading/trailing whitespace (the artifact actually seen
    in practice — a dashboard-introduced trailing newline) and never
    touches interior characters, so a password containing a legitimate
    special character (percent-encoded or not) is never altered. If
    control characters remain anywhere after that strip, the value is
    corrupted beyond what a safe strip can fix, and _build_dsn() below
    raises NWISDatabaseMisconfigured rather than silently passing a
    mangled DSN to psycopg."""
    return raw.strip()


def _build_dsn() -> Optional[str]:
    explicit_raw = os.environ.get("NWIS_DATABASE_URL")
    if explicit_raw:
        explicit = _sanitize_dsn_env_value(explicit_raw)
        if not explicit:
            raise NWISDatabaseMisconfigured(
                "NWIS_DATABASE_URL is set but contains only whitespace after stripping."
            )
        if _CONTROL_CHARS_RE.search(explicit):
            raise NWISDatabaseMisconfigured(
                "NWIS_DATABASE_URL contains an embedded control character (newline, "
                "tab, or similar) after stripping leading/trailing whitespace -- this "
                "is not a valid connection string and WILL silently corrupt the "
                "database name or another field if used as-is (psycopg's parser does "
                "not reject this; it folds the stray character into the last field). "
                "This is almost always introduced by a dashboard/platform environment- "
                "variable field mangling a pasted value. Re-enter NWIS_DATABASE_URL as "
                "a single line with no trailing newline."
            )
        if conninfo_to_dict is not None:
            try:
                conninfo_to_dict(explicit)
            except Exception as exc:
                raise NWISDatabaseMisconfigured(
                    f"NWIS_DATABASE_URL does not parse as a valid PostgreSQL "
                    f"connection string: {exc}"
                ) from exc
        return explicit

    host = os.environ.get("NWIS_DB_HOST")
    if not host:
        return None  # no DB configuration at all — stay on the in-memory store

    port = os.environ.get("NWIS_DB_PORT", "5433")  # matches docker-compose.yml's host port
    dbname = os.environ.get("NWIS_DB_NAME", "nwis")
    user = os.environ.get("NWIS_DB_USER", "nwis")
    password = os.environ.get("NWIS_DB_PASSWORD", "")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


# _build_dsn() is deliberately NOT allowed to raise past this point. This
# module's own design principle (see file docstring) is that a DB problem
# must never crash the whole process at import time -- the in-memory store
# is a fully supported fallback. A genuine misconfiguration (caught above)
# is therefore converted into a loud, impossible-to-miss startup log line
# plus a distinct is_configured()/healthcheck() state (see below), instead
# of either a silent corrupt-DSN connection attempt (the original bug) or
# a hard process crash (which would be a worse regression -- it would also
# take down every feature that doesn't need the database at all).
_DSN_MISCONFIGURED_DETAIL: Optional[str] = None
try:
    _DSN = _build_dsn()
except NWISDatabaseMisconfigured as exc:
    _DSN = None
    _DSN_MISCONFIGURED_DETAIL = str(exc)
    logger.critical(
        f"NWIS_DATABASE_URL is set but misconfigured -- refusing to attempt a "
        f"connection that would silently corrupt in a confusing way. Falling back "
        f"to the in-memory store until this is fixed. Detail: {exc}"
    )

_pool: Optional["ConnectionPool"] = None


def is_configured() -> bool:
    return _DSN is not None


def get_pool() -> "ConnectionPool":
    """Lazily create (once) and return the process-wide connection pool.

    Raises NWISDatabaseMisconfigured if NWIS_DATABASE_URL was set but failed
    validation at import time (see _build_dsn()), NWISDatabaseNotConfigured
    if no DSN is set at all, or NWISDatabaseUnavailable if psycopg itself
    isn't installed. Does NOT eagerly connect at import time — that would
    make importing this module fail the whole server process if the DB
    happens to be down, for a feature (the migrated vertical slice) that is
    opt-in.
    """
    global _pool
    if _DSN_MISCONFIGURED_DETAIL is not None:
        raise NWISDatabaseMisconfigured(_DSN_MISCONFIGURED_DETAIL)
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

    Three distinct states are reported, not two — "never configured" and
    "configured but broken" must not look identical to a caller, per this
    project's own established tri-state-honesty pattern (see
    NWISDatabaseMisconfigured's docstring for why: a misconfigured DSN
    looks exactly like "not configured" from is_configured() alone, which
    would hide a real, fixable bug behind the same payload this endpoint
    already uses for the fully-expected "no database, running in memory
    mode" case):
      - never configured:        {"configured": False, "reachable": None}
      - configured but malformed: {"configured": True, "reachable": False,
                                    "error": "NWISDatabaseMisconfigured"}
      - configured, DB down:      {"configured": True, "reachable": False,
                                    "error": <other exception class name>}
      - configured, DB up:        {"configured": True, "reachable": True}

    The "error" field (Pass 2 hardening) is the exception's CLASS NAME only,
    not str(exc) — psycopg's connection-failure messages include host/port/
    user (confirmed not the password, but still internal connection detail
    that shouldn't sit in a client-facing JSON body). Full detail is always
    in the server log line below; this function's return value is what a
    caller actually sees.
    """
    if _DSN_MISCONFIGURED_DETAIL is not None:
        return {"configured": True, "reachable": False, "error": "NWISDatabaseMisconfigured"}
    if not is_configured():
        return {"configured": False, "reachable": None}
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"configured": True, "reachable": True}
    except Exception as exc:
        logger.warning(f"Database healthcheck failed: {exc}")
        return {"configured": True, "reachable": False, "error": type(exc).__name__}
