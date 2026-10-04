"""
Concurrent requests across every service stay correct, and request handling
never touches the Python import machinery's state.

Why this matters: the old design switched sys.path per request, which is
shared mutable process state -- two in-flight requests for different services
could, in principle, interfere. These tests drive a mixed workload (the
NWIS engines that used to be the collision hot-spot, document intelligence,
physics/predictive, evidence, aggregate health) concurrently and assert:

  * every response is correct FOR ITS OWN request (validated per endpoint),
  * sys.path is never mutated at all -- not even transiently and restored --
    because it is replaced by a recording list for the duration of the test.

Kind: contract. Two flavours of concurrency, neither using a real socket:
  - asyncio.gather over httpx.AsyncClient(ASGITransport) -- interleaved requests
  - a thread pool, one TestClient (own event-loop thread) per worker -- true
    parallel threads
"""
from __future__ import annotations

import asyncio
import random
import sys
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core import auth

pytestmark = pytest.mark.contract


class RecordingPath(list):
    """Drop-in sys.path that records every mutating call, so even a transient
    insert-then-restore (the old per-request mechanism) is detected."""

    def __init__(self, items):
        super().__init__(items)
        self.mutations: list[str] = []

    def _record(self, name):
        self.mutations.append(name)

    def append(self, *a):
        self._record("append"); return super().append(*a)

    def extend(self, *a):
        self._record("extend"); return super().extend(*a)

    def insert(self, *a):
        self._record("insert"); return super().insert(*a)

    def pop(self, *a):
        self._record("pop"); return super().pop(*a)

    def remove(self, *a):
        self._record("remove"); return super().remove(*a)

    def clear(self):
        self._record("clear"); return super().clear()

    def __setitem__(self, *a):
        self._record("__setitem__"); return super().__setitem__(*a)

    def __delitem__(self, *a):
        self._record("__delitem__"); return super().__delitem__(*a)

    def __iadd__(self, *a):
        self._record("__iadd__"); return super().__iadd__(*a)

    def sort(self, *a, **k):
        self._record("sort"); return super().sort(*a, **k)

    def reverse(self):
        self._record("reverse"); return super().reverse()


def _catalog(store, key):
    """(label, url, validator) -- every validator checks the response belongs to ITS request."""
    n_wells = len(store.all_wells)
    return [
        ("v1 health", "/api/v1/health", lambda b: b["components"]["pymupdf"]["status"] == "ok"),
        ("v1 templates", "/api/v1/templates", lambda b: isinstance(b["total_templates"], int)),
        ("v2 wells", "/api/v2/wells", lambda b: b["total"] == n_wells),
        ("v2 slash id", "/api/v2/wells/15%2F9-F-12", lambda b: b["well"]["well_id"] == "15/9-F-12"),
        ("v2 offset_rank", "/api/v2/offset_rank/WELL-HGJ-012?depth=1500",
         lambda b: b["active_well_id"] == "WELL-HGJ-012" and b["total_ranked"] > 0),
        ("v2 strat track", "/api/v2/stratigraphic_depth_track/WELL-HGJ-012?depth=1500", lambda b: b["wells_aligned"] > 0),
        ("v2 corridors", "/api/v2/corridors/WELL-HGJ-012?depth=1500", lambda b: b["well_id"] == "WELL-HGJ-012"),
        ("v2 analyze", "/api/v2/analyze/WELL-HGJ-012?depth=1500", lambda b: b["active_well_id"] == "WELL-HGJ-012"),
        ("v2 events", "/api/v2/events?hazard_type=MUD_LOSS", lambda b: isinstance(b["total"], int)),
        ("v3 physics status", "/api/v3/physics/status", lambda b: isinstance(b["is_running"], bool)),
        ("v3 predictive models", "/api/v3/predictive/models",
         lambda b: isinstance(b, list) and {m["model_id"] for m in b} >= {"baseline_hazard_rules"}),
        ("evidence health", "/api/evidence/health", lambda b: b["status"] == "healthy"),
        ("aggregate health", "/health", lambda b: set(b["modules"]) == {
            "document_intelligence", "nwis_backend", "physics_predictive", "evidence"}),
    ]


@pytest.fixture()
def workload(nwis_store_loaded, keyed_auth, monkeypatch):
    # The general limiter is 60/min per key; keep the workload under it and start clean.
    auth.rate_limit_general.reset()
    auth.rate_limit_physics.reset()
    recording = RecordingPath(sys.path)
    monkeypatch.setattr(sys, "path", recording)
    yield _catalog(nwis_store_loaded, keyed_auth), {"X-API-Key": keyed_auth}, recording
    auth.rate_limit_general.reset()
    auth.rate_limit_physics.reset()


@pytest.mark.asyncio
async def test_interleaved_async_requests_are_each_correct_and_never_mutate_sys_path(asgi_app, workload):
    catalog, headers, recording = workload
    rng = random.Random(1234)
    jobs = []
    for _ in range(4):  # 4 rounds x 13 requests = 52 interleaved requests (7 hit the 60/min NWIS limiter per round)
        round_ = list(catalog)
        rng.shuffle(round_)
        jobs.extend(round_)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=asgi_app), base_url="http://test", headers=headers, timeout=120) as client:
        async def one(label, url, check):
            resp = await client.get(url)
            assert resp.status_code == 200, f"{label}: HTTP {resp.status_code} {resp.text[:200]}"
            assert check(resp.json()), f"{label}: response did not belong to this request: {resp.text[:200]}"
            return label

        done = await asyncio.gather(*(one(*j) for j in jobs))

    assert len(done) == len(jobs)
    assert recording.mutations == [], f"sys.path was mutated during request handling: {recording.mutations}"


def test_parallel_threads_each_get_correct_answers_and_sys_path_is_untouched(asgi_app, workload):
    catalog, headers, recording = workload
    failures: list[str] = []

    def worker(seed: int):
        rng = random.Random(seed)
        jobs = list(catalog)
        rng.shuffle(jobs)
        client = TestClient(asgi_app)
        for label, url, check in jobs:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200 or not check(resp.json()):
                failures.append(f"[thread {seed}] {label}: HTTP {resp.status_code} {resp.text[:150]}")

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(worker, range(6)))

    assert failures == [], failures
    assert recording.mutations == [], f"sys.path was mutated during request handling: {recording.mutations}"


def test_recording_path_actually_detects_a_transient_mutation(monkeypatch):
    """Self-test: prove the detector would catch the OLD behaviour (insert, then restore)."""
    recording = RecordingPath(sys.path)
    monkeypatch.setattr(sys, "path", recording)
    saved = list(sys.path)
    sys.path.insert(0, "/some/module/root")   # what the old middleware did...
    sys.path[:] = saved                        # ...and then restored
    assert recording.mutations, "the detector failed to notice a transient sys.path mutation"
