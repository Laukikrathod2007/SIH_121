"""
Backend/requirements*.txt is the single authoritative dependency manifest.

Kind: unit (static). These checks prove the manifest is internally consistent
and COMPLETE with respect to what the code actually imports. That a clean
environment can really install it and start the app is verified separately,
by installing into a fresh virtualenv (see Backend/README.md "Verification");
a unit test cannot honestly claim that.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent

# import name -> distribution name, where they differ
IMPORT_TO_DIST = {
    "fitz": "pymupdf",
    "dotenv": "python-dotenv",
    "sklearn": "scikit-learn",
    "sentence_transformers": "sentence-transformers",
    "psycopg_pool": "psycopg-pool",
}
# imported directly but delivered by another declared package
TRANSITIVE_OK = {"starlette": "fastapi", "websockets": "uvicorn[standard]", "pytest": "dev"}
# declared but never imported by name -- required indirectly (reason recorded)
DECLARED_BUT_INDIRECT = {
    "python-multipart": "FastAPI needs it for UploadFile/Form (/api/v1/ingest)",
    "uvicorn": "ASGI server started by run.py / launchers",
    "pydantic": "FastAPI request/response models (imported by the legacy schemas)",
}
LOCAL_TOP_LEVEL = {"app", "tests"}


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_manifest(path: Path) -> set[str]:
    names = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"([A-Za-z0-9_.\-]+)", line)
        assert m, f"unparseable requirement line: {raw!r}"
        names.add(_norm(m.group(1)))
    return names


@pytest.fixture(scope="module")
def runtime_pkgs() -> set[str]:
    return _parse_manifest(BACKEND / "requirements.txt")


@pytest.fixture(scope="module")
def optional_pkgs() -> set[str]:
    return _parse_manifest(BACKEND / "requirements-optional.txt")


def test_manifest_files_exist():
    for f in ("requirements.txt", "requirements-optional.txt", "requirements-dev.txt"):
        assert (BACKEND / f).is_file(), f


def test_no_package_declared_twice_with_different_pins():
    for f in ("requirements.txt", "requirements-optional.txt", "requirements-dev.txt"):
        seen = {}
        for raw in (BACKEND / f).read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            name = _norm(re.match(r"([A-Za-z0-9_.\-]+)", line).group(1))
            assert name not in seen, f"{f}: {name} declared twice: {seen[name]!r} and {line!r}"
            seen[name] = line


def test_runtime_and_optional_sets_do_not_overlap(runtime_pkgs, optional_pkgs):
    assert not (runtime_pkgs & optional_pkgs)


def test_dev_manifest_includes_the_runtime_manifest():
    assert "-r requirements.txt" in (BACKEND / "requirements-dev.txt").read_text(encoding="utf-8")


def _third_party_imports() -> dict[str, set[str]]:
    stdlib = set(sys.stdlib_module_names)
    files = list((BACKEND / "app").rglob("*.py")) + [BACKEND / "run.py"]
    for legacy in ("01_document_intelligence", "02_nwis_backend", "04_physics_engine", "05_predictive_analytics"):
        files += [p for p in (REPO / "modules" / legacy).rglob("*.py")
                  if "tests" not in p.parts and "__pycache__" not in p.parts]
    uses: dict[str, set[str]] = {}
    for p in files:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8-sig"))
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            names = []
            if isinstance(n, ast.Import):
                names = [a.name.split(".")[0] for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                names = [n.module.split(".")[0]]
            for name in names:
                if name in stdlib or name in LOCAL_TOP_LEVEL:
                    continue
                uses.setdefault(name, set()).add(p.relative_to(REPO).as_posix())
    return uses


# Names that are the legacy trees' own sibling packages/scripts, not PyPI packages.
LEGACY_LOCAL_NAMES = {
    "models", "api", "db", "engines", "ml", "live", "search", "auth", "data_store", "orchestrator",
    "pipeline", "simulation", "data_pipeline", "predictive", "server", "generate_testbed", "benchmarks",
    "run_server", "validate_module01", "train_hazard_models",
}


def test_every_third_party_import_is_declared(runtime_pkgs, optional_pkgs):
    declared = runtime_pkgs | optional_pkgs
    missing = {}
    for name, files in _third_party_imports().items():
        if name in LEGACY_LOCAL_NAMES:
            continue
        dist = _norm(IMPORT_TO_DIST.get(name, name))
        if dist in declared or name in TRANSITIVE_OK:
            continue
        missing[name] = sorted(files)[:3]
    assert not missing, f"imported but not declared in requirements*.txt: {missing}"


def test_every_runtime_dependency_is_actually_needed(runtime_pkgs):
    """No unnecessary dependencies: each runtime package is imported by name
    somewhere, or is on the documented 'required indirectly' list."""
    imported_dists = {_norm(IMPORT_TO_DIST.get(n, n)) for n in _third_party_imports()}
    unused = {p for p in runtime_pkgs if p not in imported_dists and p not in {_norm(k) for k in DECLARED_BUT_INDIRECT}}
    assert not unused, f"declared in requirements.txt but never imported (and not on the indirect list): {sorted(unused)}"


def test_old_unneeded_packages_are_not_reintroduced(runtime_pkgs):
    # Never imported by any integrated code; the old per-module manifests listed them.
    for pkg in ("aiofiles", "orjson", "pydantic-settings", "pillow"):
        assert pkg not in runtime_pkgs
