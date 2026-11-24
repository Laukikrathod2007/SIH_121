"""
Shared authentication / rate limiting / production-config logic (app.core).

Kind: unit -- no app, no network. The dependencies are plain async functions,
so they are exercised directly with a constructed Starlette Request.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core import auth, config

pytestmark = pytest.mark.unit


def _request(ip: str = "10.0.0.1") -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": [], "client": (ip, 1234)})


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- require_api_key

def test_auth_disabled_when_no_key_configured(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "")
    assert auth.auth_enabled() is False
    assert _run(auth.require_api_key(None)) is None  # open by default (local dev)


def test_missing_key_is_401(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "secret-value")
    with pytest.raises(HTTPException) as exc:
        _run(auth.require_api_key(None))
    assert exc.value.status_code == 401


def test_wrong_key_is_401(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "secret-value")
    with pytest.raises(HTTPException) as exc:
        _run(auth.require_api_key("not-the-secret"))
    assert exc.value.status_code == 401
    assert "secret-value" not in str(exc.value.detail)  # never echo the real key


def test_correct_key_is_accepted(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "secret-value")
    assert _run(auth.require_api_key("secret-value")) is None


def test_prefix_of_key_is_rejected(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "secret-value")
    with pytest.raises(HTTPException):
        _run(auth.require_api_key("secret"))


# ---------------------------------------------------------------- rate limiter

def test_rate_limiter_blocks_after_max_requests_with_429():
    limiter = auth.make_rate_limiter("UNIT_TEST_RL", default_max_requests=3)
    for _ in range(3):
        _run(limiter(_request(), None))
    with pytest.raises(HTTPException) as exc:
        _run(limiter(_request(), None))
    assert exc.value.status_code == 429


def test_rate_limiter_buckets_are_per_identity():
    limiter = auth.make_rate_limiter("UNIT_TEST_RL2", default_max_requests=1)
    _run(limiter(_request("10.0.0.1"), None))
    _run(limiter(_request("10.0.0.2"), None))            # different client: own bucket
    _run(limiter(_request("10.0.0.3"), "some-api-key"))   # keyed by API key when present
    with pytest.raises(HTTPException):
        _run(limiter(_request("10.0.0.1"), None))


def test_rate_limiter_reset_forgets_history():
    limiter = auth.make_rate_limiter("UNIT_TEST_RL3", default_max_requests=1)
    _run(limiter(_request(), None))
    limiter.reset()
    _run(limiter(_request(), None))  # allowed again


def test_each_route_class_keeps_its_original_ceiling():
    """The three modules deliberately had different limits; unification must not flatten them."""
    assert getattr(auth.rate_limit_ingest, "default_max_requests", auth.rate_limit_ingest.max_requests) == 20     # M01 upload (can trigger paid cloud calls)
    assert getattr(auth.rate_limit_general, "default_max_requests", auth.rate_limit_general.max_requests) == 60    # M02 analysis/queries
    assert getattr(auth.rate_limit_physics, "default_max_requests", auth.rate_limit_physics.max_requests) == 600   # M04 physics: legitimately high-frequency polling
    assert getattr(auth.rate_limit_agent, "default_max_requests", auth.rate_limit_agent.max_requests) == 10     # Agent chat (LLM tool-calling turns, CPU-heavy)
    for limiter in (auth.rate_limit_ingest, auth.rate_limit_general, auth.rate_limit_physics, auth.rate_limit_agent):
        assert limiter.window_seconds == 60


def test_limiters_are_independent_objects():
    assert len({id(auth.rate_limit_ingest), id(auth.rate_limit_general), id(auth.rate_limit_physics), id(auth.rate_limit_agent)}) == 4


def test_legacy_auth_modules_re_export_the_shared_objects_not_copies():
    """The old per-module auth.py files must be thin re-exports, so a route's
    Depends(require_api_key) is the SAME function object everywhere."""
    from app.modules.document_intelligence.api import auth as m01
    from app.modules.nwis import auth as m02
    from app.modules.physics.api import auth as m04

    assert m01.require_api_key is auth.require_api_key
    assert m02.require_api_key is auth.require_api_key
    assert m04.require_api_key is auth.require_api_key
    assert m01.rate_limit_ingest is auth.rate_limit_ingest
    assert m01.rate_limit_general is auth.rate_limit_general
    assert m02.rate_limit is auth.rate_limit_general
    assert m02.rate_limit_agent is auth.rate_limit_agent
    assert m04.rate_limit is auth.rate_limit_physics


# ---------------------------------------------------------------- production config

def test_production_refuses_to_start_without_api_key(monkeypatch):
    monkeypatch.setattr(config, "IS_PRODUCTION", True)
    monkeypatch.setattr(auth, "API_KEY", "")
    with pytest.raises(RuntimeError) as exc:
        config.startup_security_check()
    assert "NWIS_API_KEY" in str(exc.value)  # actionable message


def test_production_starts_with_api_key(monkeypatch):
    monkeypatch.setattr(config, "IS_PRODUCTION", True)
    monkeypatch.setattr(auth, "API_KEY", "set")
    config.startup_security_check()  # no raise


def test_development_allows_missing_api_key(monkeypatch):
    monkeypatch.setattr(config, "IS_PRODUCTION", False)
    monkeypatch.setattr(auth, "API_KEY", "")
    config.startup_security_check()  # no raise


def _capture_warnings():
    """loguru doesn't integrate with pytest's `caplog` (it isn't stdlib
    logging) -- the documented way to assert on a loguru message in a test
    is to add a temporary sink and inspect what it received."""
    from loguru import logger

    records: list[str] = []
    sink_id = logger.add(lambda msg: records.append(msg.record["message"]), level="WARNING")
    return records, sink_id


def test_unset_nwis_env_with_no_api_key_warns_loudly_but_does_not_raise(monkeypatch):
    """Fix 1: an ambiguous NWIS_ENV (not 'production', not a recognized dev
    alias) with no API key must not fail silently -- this is the exact
    configuration landmine (a deploy target that forgot to set
    NWIS_ENV=production) that left every route unauthenticated with zero
    signal. Must warn, must not raise (would break real keyless local dev)."""
    from loguru import logger

    monkeypatch.setattr(config, "IS_PRODUCTION", False)
    monkeypatch.setattr(config, "NWIS_ENV", "staging")  # not in KNOWN_DEV_ENVS, not "production"
    monkeypatch.setattr(auth, "API_KEY", "")
    records, sink_id = _capture_warnings()
    try:
        config.startup_security_check()  # no raise
    finally:
        logger.remove(sink_id)
    joined = "\n".join(records)
    assert "NWIS_ENV" in joined
    assert "UNAUTHENTICATED" in joined


def test_recognized_dev_env_with_no_api_key_still_warns_about_the_missing_key(monkeypatch):
    """Even a deliberately-dev NWIS_ENV (e.g. 'dev', the actual default)
    should still get the loud "every route is unauthenticated" warning when
    no key is configured -- it's correct for local dev, but must never be
    silent about it, since the same code path serves real deploys too."""
    from loguru import logger

    monkeypatch.setattr(config, "IS_PRODUCTION", False)
    monkeypatch.setattr(config, "NWIS_ENV", "dev")
    monkeypatch.setattr(auth, "API_KEY", "")
    records, sink_id = _capture_warnings()
    try:
        config.startup_security_check()  # no raise
    finally:
        logger.remove(sink_id)
    assert any("UNAUTHENTICATED" in r for r in records)
    assert not any("NWIS_ENV" in r for r in records)  # "dev" is a known alias, no NWIS_ENV warning needed


def test_recognized_dev_env_with_api_key_set_warns_about_neither(monkeypatch):
    from loguru import logger

    monkeypatch.setattr(config, "IS_PRODUCTION", False)
    monkeypatch.setattr(config, "NWIS_ENV", "test")
    monkeypatch.setattr(auth, "API_KEY", "a-real-key")
    records, sink_id = _capture_warnings()
    try:
        config.startup_security_check()  # no raise
    finally:
        logger.remove(sink_id)
    assert records == []
