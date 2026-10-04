"""
Canonical namespaces for the four legacy service trees.

The source code of these services lives, unchanged and in place, under the
top-level `modules/` directory (see app/core/config.py: M01_ROOT, M02_ROOT,
M04_ROOT, M05_ROOT). Their directory names start with a digit
(`01_document_intelligence`, ...), which is not a valid Python identifier,
and each service has generically named top-level packages (`models`, `api`,
...) that collided when co-imported. Each subpackage here is a thin adapter:
its `__path__` is pointed at the legacy directory, so the ordinary import
system resolves e.g. `app.modules.nwis.engines.dors_engine` to
`modules/02_nwis_backend/engines/dors_engine.py`.

  app.modules.document_intelligence  ->  modules/01_document_intelligence/
  app.modules.nwis                   ->  modules/02_nwis_backend/
  app.modules.physics                ->  modules/04_physics_engine/
  app.modules.predictive_analytics   ->  modules/05_predictive_analytics/

Every internal import in those trees is written against these canonical
names (never a bare `models` / `api` / `db`), so resolution is the same
regardless of import order, working directory, or which request arrives
first -- and nothing mutates sys.path or sys.modules at runtime.
"""
