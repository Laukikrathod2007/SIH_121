"""
The Python import architecture, verified.

Problem being guarded against: four legacy service trees with identically named
top-level packages (`models` x3, `api` x2, ...) once had to be kept apart with
request-scoped sys.path switching. They now live behind canonical packages
(app.modules.document_intelligence / nwis / physics / predictive_analytics), and
these tests prove the properties that make that safe:

  * the canonical entry point imports every module package
  * resolution is identical for EVERY import order (fresh interpreter each)
  * no bare legacy name (`models`, `api`, `db`, ...) ever appears in sys.modules
  * no module file is loaded twice under two names
  * importing the app does not touch sys.path or start any task
  * no application code mutates sys.path / sys.modules (static scan)

Kind: unit. Import-order and sys.path checks run in a FRESH subprocess so they
cannot be contaminated by whatever the pytest process already imported.
"""
from __future__ import annotations

import ast
import importlib
import itertools
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent

LEGACY_TO_CANONICAL = {
    "01_document_intelligence": "document_intelligence",
    "02_nwis_backend": "nwis",
    "04_physics_engine": "physics",
    "05_predictive_analytics": "predictive_analytics",
}
BARE_LEGACY_NAMES = (
    "models", "api", "db", "engines", "ml", "live", "search", "auth", "data_store",
    "orchestrator", "pipeline", "simulation", "data_pipeline", "predictive",
)

# Key modules of every service, including the ones that used to be reached only
# through lazy (inside-function) imports and collided on `models`.
ENTRY_MODULES = [
    "app.modules.document_intelligence.api.server",
    "app.modules.document_intelligence.pipeline.orchestrator",
    "app.modules.document_intelligence.models.schemas",
    "app.modules.nwis.server",
    "app.modules.nwis.engines.dors_engine",
    "app.modules.nwis.engines.risk_corridor_engine",
    "app.modules.nwis.ml.hazard_predictor",
    "app.modules.nwis.search.knowledge_search",
    "app.modules.nwis.live.replay_engine",
    "app.modules.nwis.db.service",
    "app.modules.nwis.models.schemas",
    "app.modules.physics.api.server",
    "app.modules.physics.simulation.engine",
    "app.modules.physics.models.state",
    "app.modules.predictive_analytics.predictive.realtime_inference",
]


def _run_fresh(code: str) -> subprocess.CompletedProcess:
    """Run `code` in a brand-new interpreter rooted at Backend/ (not via sys.path edits)."""
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        cwd=BACKEND, capture_output=True, text=True, timeout=300,
    )


# ---------------------------------------------------------------------------
# 1. canonical entry point imports all internal modules
# ---------------------------------------------------------------------------

def test_canonical_entry_point_imports_every_module_package(asgi_app):
    for name in ENTRY_MODULES:
        module = importlib.import_module(name)
        assert module.__name__ == name


def test_canonical_modules_resolve_to_the_legacy_source_tree_without_copying():
    """Each adapter package's __path__ is the legacy directory -- the code is
    reached in place (nothing moved or duplicated)."""
    for legacy, canonical in LEGACY_TO_CANONICAL.items():
        pkg = importlib.import_module(f"app.modules.{canonical}")
        assert [Path(p).resolve() for p in pkg.__path__] == [(REPO / "modules" / legacy).resolve()]


# ---------------------------------------------------------------------------
# 2. resolution does not depend on import order
# ---------------------------------------------------------------------------

# (module, expected-file-suffix) -- three different `models` packages plus
# modules that import their OWN `models` at their top level.
ORDER_PROBES = [
    ("app.modules.nwis.models.schemas", "02_nwis_backend/models/schemas.py"),
    ("app.modules.document_intelligence.models.schemas", "01_document_intelligence/models/schemas.py"),
    ("app.modules.physics.models.config", "04_physics_engine/models/config.py"),
    ("app.modules.nwis.engines.dors_engine", "02_nwis_backend/engines/dors_engine.py"),
    ("app.modules.document_intelligence.pipeline.orchestrator", "01_document_intelligence/pipeline/orchestrator.py"),
]


@pytest.mark.parametrize("order", list(itertools.islice(itertools.permutations(range(len(ORDER_PROBES))), 0, None, 24)))
def test_import_order_never_changes_which_module_a_name_resolves_to(order):
    """Fresh interpreter per order: whichever package is imported first, every
    module resolves to its own file, and modules that import `models` internally
    are bound to THEIR service's classes (not another service's)."""
    probes = [ORDER_PROBES[i] for i in order]
    code = f"""
        import importlib
        probes = {probes!r}
        loaded = {{}}
        for name, suffix in probes:
            loaded[name] = importlib.import_module(name)
        for name, suffix in probes:
            f = loaded[name].__file__.replace("\\\\", "/")
            assert f.endswith(suffix), (name, f)
        nwis = loaded["app.modules.nwis.models.schemas"]
        docint = loaded["app.modules.document_intelligence.models.schemas"]
        dors = loaded["app.modules.nwis.engines.dors_engine"]
        orch = loaded["app.modules.document_intelligence.pipeline.orchestrator"]
        assert nwis is not docint
        assert dors.Well is nwis.Well                      # NWIS engine bound to NWIS models
        assert orch.DocumentExtractionResult is docint.DocumentExtractionResult
        assert not hasattr(docint, "Well") and not hasattr(nwis, "DocumentExtractionResult")
        print("ok")
    """
    proc = _run_fresh(code)
    assert proc.returncode == 0 and "ok" in proc.stdout, proc.stderr[-2000:]


# ---------------------------------------------------------------------------
# 3. no bare legacy names; 4. no duplicate module instances
# ---------------------------------------------------------------------------

def test_no_bare_legacy_module_names_after_importing_the_app():
    code = f"""
        import sys
        import app.main
        bare = [n for n in {BARE_LEGACY_NAMES!r} if n in sys.modules]
        print("BARE:", bare)
    """
    proc = _run_fresh(code)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "BARE: []" in proc.stdout, proc.stdout[-500:]


def test_no_module_file_is_loaded_under_two_names(asgi_app):
    """The same canonical module must exist exactly once in sys.modules."""
    by_file: dict[str, list[str]] = {}
    legacy_roots = [(REPO / "modules" / d).resolve() for d in LEGACY_TO_CANONICAL]
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        p = Path(f).resolve()
        if any(r == p or r in p.parents for r in legacy_roots):
            by_file.setdefault(str(p), []).append(name)
    assert by_file, "expected legacy-tree modules to be loaded"
    duplicated = {f: names for f, names in by_file.items() if len(names) > 1}
    assert not duplicated, duplicated
    # ...and every one of them is under the canonical namespace.
    not_canonical = {f: n for f, n in by_file.items() if not n[0].startswith("app.modules.")}
    assert not not_canonical, not_canonical


# ---------------------------------------------------------------------------
# 5. importing the app does not mutate sys.path or start anything
# ---------------------------------------------------------------------------

def test_importing_the_app_does_not_change_sys_path():
    code = """
        import sys
        before = list(sys.path)
        import app.main
        print("SAME:", before == list(sys.path))
    """
    proc = _run_fresh(code)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "SAME: True" in proc.stdout


def test_importing_the_app_starts_no_simulation_or_tasks():
    code = """
        import app.main
        from app.integrations import m04_physics_predictive as phys
        from app.modules.physics.api import server as ps
        print("LOOP:", phys.sim_loop_running(), "RUNNING:", ps.runtime.is_running)
    """
    proc = _run_fresh(code)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "LOOP: False RUNNING: False" in proc.stdout


# ---------------------------------------------------------------------------
# 6. static: application code never mutates sys.path / sys.modules
# ---------------------------------------------------------------------------

# Standalone CLI/debug entry points that deliberately bootstrap Backend/ onto
# sys.path ONCE at process start (never inside the served app, never per
# request). Each is documented in the file itself. Anything not listed here
# must be free of sys.path / sys.modules mutation.
LAUNCHER_ALLOWLIST = {
    "modules/01_document_intelligence/run_server.py",
    "modules/01_document_intelligence/validate_module01.py",
    "modules/01_document_intelligence/benchmarks/run_benchmark.py",
    "modules/02_nwis_backend/run_server.py",
    "modules/02_nwis_backend/ml/train_hazard_models.py",
    "modules/04_physics_engine/run_server.py",
}


def _mutations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    hits = []

    def is_sys_attr(node, attr):
        return (isinstance(node, ast.Attribute) and node.attr == attr
                and isinstance(node.value, ast.Name) and node.value.id == "sys")

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if is_sys_attr(node.func.value, "path") and node.func.attr in {"insert", "append", "extend", "remove", "pop", "clear"}:
                hits.append(f"sys.path.{node.func.attr}() line {node.lineno}")
            if is_sys_attr(node.func.value, "modules") and node.func.attr in {"pop", "update", "setdefault", "clear"}:
                hits.append(f"sys.modules.{node.func.attr}() line {node.lineno}")
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.Delete)):
            targets = node.targets if hasattr(node, "targets") else [node.target]
            for t in targets:
                base = t.value if isinstance(t, ast.Subscript) else t
                if is_sys_attr(base, "path") or is_sys_attr(base, "modules"):
                    hits.append(f"assignment/deletion on sys.{base.attr} line {node.lineno}")
    return hits


def _served_source_files() -> list[Path]:
    files = [p for p in (BACKEND / "app").rglob("*.py")]
    for legacy in LEGACY_TO_CANONICAL:
        for p in (REPO / "modules" / legacy).rglob("*.py"):
            rel = p.relative_to(REPO).as_posix()
            if "__pycache__" in p.parts or "tests" in p.parts or rel in LAUNCHER_ALLOWLIST:
                continue
            files.append(p)
    return files


def test_no_served_code_mutates_sys_path_or_sys_modules():
    offenders = {}
    for p in _served_source_files():
        hits = _mutations(p)
        if hits:
            offenders[p.relative_to(REPO).as_posix()] = hits
    assert not offenders, offenders


def test_launcher_allowlist_entries_exist_and_still_need_listing():
    """Keeps the allowlist honest: a stale or unnecessary entry fails the test."""
    for rel in LAUNCHER_ALLOWLIST:
        p = REPO / rel
        assert p.exists(), f"allowlisted launcher missing: {rel}"
        assert _mutations(p), f"{rel} no longer mutates sys.path -- remove it from LAUNCHER_ALLOWLIST"


def test_no_legacy_bare_imports_remain_in_any_legacy_source_file():
    """Every cross-package import inside the legacy trees uses the canonical
    app.modules.* names (an ambiguous bare `from models...` would re-open the
    original collision)."""
    pattern_roots = set(BARE_LEGACY_NAMES)
    offenders = {}
    for legacy in LEGACY_TO_CANONICAL:
        base = REPO / "modules" / legacy
        own = {c.name for c in base.iterdir() if (c.is_dir() and (c / "__init__.py").exists()) or c.suffix == ".py"}
        own = {n[:-3] if n.endswith(".py") else n for n in own} & pattern_roots
        for p in base.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8-sig"))
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                mod = None
                if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                    mod = n.module
                elif isinstance(n, ast.Import):
                    for a in n.names:
                        if a.name.split(".")[0] in own:
                            offenders.setdefault(p.relative_to(REPO).as_posix(), []).append(f"import {a.name} line {n.lineno}")
                if mod and mod.split(".")[0] in own:
                    offenders.setdefault(p.relative_to(REPO).as_posix(), []).append(f"from {mod} line {n.lineno}")
    assert not offenders, offenders
