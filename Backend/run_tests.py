"""
Run EVERY backend test suite, each in its own pytest process, and report a
combined result:

    cd Backend
    python run_tests.py                 # all suites
    python run_tests.py -m "not integration and not db"   # extra args go to pytest

Suites
  backend              Backend/tests            (unit + contract + integration)
  document_intelligence  modules/01_document_intelligence/tests
  nwis                 modules/02_nwis_backend/tests
  physics              modules/04_physics_engine/tests
  predictive_analytics modules/05_predictive_analytics/tests

Why separate processes: the four legacy suites each contain a package named
`tests`, and each mutates its own module-level singletons; one process per
suite keeps them from interfering. The exit code is non-zero if ANY suite
fails. Skips (e.g. `integration` tests when no server is running, `db` tests
when no PostgreSQL is reachable) are reported by pytest with their reasons and
are NOT counted as passes.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
REPO = BACKEND.parent

SUITES = [
    ("backend", BACKEND / "tests"),
    ("document_intelligence", REPO / "modules" / "01_document_intelligence" / "tests"),
    ("nwis", REPO / "modules" / "02_nwis_backend" / "tests"),
    ("physics", REPO / "modules" / "04_physics_engine" / "tests"),
    ("predictive_analytics", REPO / "modules" / "05_predictive_analytics" / "tests"),
]


def main() -> int:
    extra = sys.argv[1:]
    failures = []
    for name, path in SUITES:
        print(f"\n{'=' * 78}\n SUITE: {name}   ({path.relative_to(REPO)})\n{'=' * 78}", flush=True)
        # `-c` makes Backend/pytest.ini (import root, import mode, markers)
        # apply to EVERY suite, including the legacy ones that live outside
        # Backend/ (pytest would otherwise pick rootdir/ini from the test path).
        code = subprocess.call(
            [sys.executable, "-m", "pytest", "-c", str(BACKEND / "pytest.ini"), str(path), *extra],
            cwd=BACKEND,
        )
        if code not in (0, 5):  # 5 = no tests collected (e.g. everything deselected)
            failures.append((name, code))
    print("\n" + "=" * 78)
    if failures:
        print(" FAILED suites: " + ", ".join(f"{n} (exit {c})" for n, c in failures))
        return 1
    print(" ALL SUITES PASSED (skips, if any, are listed above with reasons)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
