"""
Repository layer — the ONLY place in this package that writes raw SQL.
Services (service.py) call these; API routes (server.py) never touch a
database connection or a SQL string directly.

Distance semantics: PostGIS geography ST_Distance() computes a geodesic
(spheroidal, WGS84) great-circle distance in meters — the same quantity
engines/dors_engine.py's haversine_km() approximates on a perfect sphere
(R=6371.0 km). The two differ by at most ~0.3%, which is immaterial at the
10-25km offset-well scale this system operates at, but is called out here
explicitly per the task requirement not to introduce a second, silently
different geographic formula: this IS a different formula (geodesic vs.
spherical), chosen deliberately because it is PostGIS's native, indexable
one, not reinvented in Python. ST_DWithin() on the same geography column
uses the same geodesic calculation for the hard filter, so the filter and
the returned distance are always consistent with each other.
"""

from __future__ import annotations

from typing import Any, Optional

from psycopg.rows import dict_row


class WellRepository:
    """Data access for the `wells` table and its PostGIS-backed geospatial
    queries. One repository instance per request-scoped connection."""

    def __init__(self, conn):
        self._conn = conn

    def get_by_id(self, well_id: str) -> Optional[dict[str, Any]]:
        """Fetch one well by its business-key well_id (preserves IDs
        containing '/', '-', '_' — e.g. real Volve IDs like "15/9-F-12" —
        since well_id is TEXT PRIMARY KEY, never rewritten or parsed)."""
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    w.well_id, w.well_name, w.source_type, w.status, w.well_type,
                    w.kb_elevation_m, w.total_depth_md_m, w.spud_date, w.completion_date,
                    w.witsml_uid,
                    ST_Y(w.surface_location::geometry) AS surface_lat,
                    ST_X(w.surface_location::geometry) AS surface_lon,
                    f.field_name, f.field_code, f.basin,
                    o.operator_name, o.operator_code
                FROM wells w
                LEFT JOIN fields f ON f.field_id = w.field_id
                LEFT JOIN operators o ON o.operator_id = w.operator_id
                WHERE w.well_id = %s
                """,
                (well_id,),
            )
            return cur.fetchone()

    def list_all(
        self,
        field: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List all wells, optionally filtered — mirrors GET /api/v2/wells'
        existing field/status filter semantics exactly (case-insensitive
        substring match on field, exact case-insensitive match on status).

        Pass 5: added operator_name/witsml_uid/spud_date/completion_date —
        originally omitted here (only get_by_id selected them), but
        DbStoreSnapshot (db/service.py) needs a full Well reconstruction
        from a single list query rather than N get_by_id() round trips.
        Backward compatible: _well_row_to_api_shape already reads these
        via .get(...), so existing callers (list_wells, get_map_wells) are
        unaffected by the extra columns now present on each row."""
        sql = """
            SELECT
                w.well_id, w.well_name, w.source_type, w.status, w.well_type,
                w.kb_elevation_m, w.total_depth_md_m, w.spud_date, w.completion_date,
                w.witsml_uid,
                ST_Y(w.surface_location::geometry) AS surface_lat,
                ST_X(w.surface_location::geometry) AS surface_lon,
                f.field_name, f.field_code,
                o.operator_name, o.operator_code
            FROM wells w
            LEFT JOIN fields f ON f.field_id = w.field_id
            LEFT JOIN operators o ON o.operator_id = w.operator_id
            WHERE (%(field)s::text IS NULL OR f.field_name ILIKE '%%' || %(field)s || '%%')
              AND (%(status)s::text IS NULL OR w.status = %(status)s)
            ORDER BY w.well_id
        """
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, {"field": field, "status": status.upper() if status else None})
            return cur.fetchall()

    def nearby(
        self,
        center_well_id: str,
        max_distance_km: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Database-side geographic nearby-well query, using the center well's
        own stored surface_location rather than re-passing lat/lon — avoids
        any drift between the center well's row and the point used to
        measure distance from it.

        Preserves the already-fixed radius semantics (task requirement #10):
        this method implements the HARD filter (max_distance_km / ST_DWithin)
        only. It does not do DORS spatial-decay scoring — that stays exactly
        where it already is, in engines/dors_engine.py's score_spatial(),
        unchanged by this migration.

        max_distance_km=None returns every other well, unfiltered, ordered
        by distance ascending (nearest first) — matches GET /api/v2/map/wells'
        existing no-params behavior of returning all wells.
        """
        params: dict[str, Any] = {"center_well_id": center_well_id}
        where_clause = "w.well_id != %(center_well_id)s"

        if max_distance_km is not None:
            params["max_distance_m"] = max_distance_km * 1000.0
            # ST_DWithin uses the same geography-type geodesic distance as
            # ST_Distance below (both operate on the `geography` column, not
            # a ::geometry cast) — the hard filter and the reported
            # distance_km are computed from the same formula, never two
            # competing ones.
            where_clause += """ AND ST_DWithin(
                w.surface_location,
                (SELECT surface_location FROM wells WHERE well_id = %(center_well_id)s),
                %(max_distance_m)s
            )"""

        limit_clause = ""
        if limit is not None:
            params["limit"] = limit
            limit_clause = "LIMIT %(limit)s"

        sql = f"""
            SELECT
                w.well_id, w.well_name, w.source_type, w.status, w.well_type,
                w.total_depth_md_m,
                ST_Y(w.surface_location::geometry) AS surface_lat,
                ST_X(w.surface_location::geometry) AS surface_lon,
                f.field_name, f.field_code,
                ST_Distance(
                    w.surface_location,
                    (SELECT surface_location FROM wells WHERE well_id = %(center_well_id)s)
                ) / 1000.0 AS distance_km
            FROM wells w
            LEFT JOIN fields f ON f.field_id = w.field_id
            WHERE {where_clause}
            ORDER BY distance_km ASC
            {limit_clause}
        """
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def event_count_by_well(self, well_ids: list[str]) -> dict[str, int]:
        """Event counts for a set of wells, for the map's `total_events`
        field — one query instead of N, unlike the in-memory store's
        per-well dict lookup, which this replaces for the DB-backed path."""
        if not well_ids:
            return {}
        rows = self._conn.execute(
            "SELECT well_id, COUNT(*) AS n FROM drilling_events "
            "WHERE well_id = ANY(%s) GROUP BY well_id",
            (well_ids,),
        ).fetchall()
        return {r[0]: r[1] for r in rows}


class TrajectoryRepository:
    """Data access for `trajectory_stations` — Pass 4 extension of the same
    DB-backed-with-memory-fallback pattern WellRepository established for
    the well/nearby-well slice. Read-only: trajectory stations are seeded
    by database/migrate_seed.py, not written by the live application."""

    def __init__(self, conn):
        self._conn = conn

    def for_well(self, well_id: str) -> list[dict[str, Any]]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT md_m, inclination_deg, azimuth_deg, tvd_m, ns_m, ew_m,
                       tvdss_m, method, source_type
                FROM trajectory_stations
                WHERE well_id = %s
                ORDER BY md_m ASC
                """,
                (well_id,),
            )
            return cur.fetchall()


class FormationRepository:
    """Data access for `formation_tops` — read-only, seeded by migrate_seed.py."""

    def __init__(self, conn):
        self._conn = conn

    def for_well(self, well_id: str) -> list[dict[str, Any]]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT formation_name, top_md_m, top_tvd_m, base_md_m, thickness_m,
                       pore_pressure_gradient_ppg, lithology, confidence, source_type
                FROM formation_tops
                WHERE well_id = %s
                ORDER BY top_md_m ASC
                """,
                (well_id,),
            )
            return cur.fetchall()

    def all_tops(self, formation_name: Optional[str] = None) -> list[dict[str, Any]]:
        sql = """
            SELECT well_id, formation_name, top_md_m, top_tvd_m, base_md_m, thickness_m,
                   pore_pressure_gradient_ppg, lithology, confidence, source_type
            FROM formation_tops
            WHERE (%(formation_name)s::text IS NULL OR formation_name ILIKE '%%' || %(formation_name)s || '%%')
            ORDER BY well_id, top_md_m ASC
        """
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, {"formation_name": formation_name})
            return cur.fetchall()


class CasingRepository:
    """Data access for `casing_programs` — read-only, seeded from
    real_data/real_casing_records_all.json by migrate_seed.py."""

    def __init__(self, conn):
        self._conn = conn

    def for_well(self, well_id: str) -> list[dict[str, Any]]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT casing_size_inches, shoe_depth_md_m, top_of_cement_md_m, source_type
                FROM casing_programs
                WHERE well_id = %s
                ORDER BY shoe_depth_md_m ASC
                """,
                (well_id,),
            )
            return cur.fetchall()

    def all_records(self) -> list[dict[str, Any]]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT well_id, casing_size_inches, shoe_depth_md_m, top_of_cement_md_m, source_type
                FROM casing_programs
                ORDER BY well_id, shoe_depth_md_m ASC
                """
            )
            return cur.fetchall()


class EventRepository:
    """Data access for `drilling_events` — Pass 5 addition. Read-only here
    (the only write path is modules/01_document_intelligence/db's
    document->knowledge-base handoff, a separate repository in a separate
    package). Every column needed to reconstruct a models.schemas
    DrillingEvent is selected explicitly — see db/service.py's
    _event_row_to_model for the mapping."""

    _COLUMNS = """
        event_id, well_id, event_type, severity, depth_start_md_m, depth_end_md_m,
        formation, raw_narrative, npt_hours, loss_rate_bbl_hr,
        mitigation_description, outcome, confidence, source_document_id,
        source_page, source_type
    """

    def __init__(self, conn):
        self._conn = conn

    def for_well(self, well_id: str) -> list[dict[str, Any]]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"SELECT {self._COLUMNS} FROM drilling_events WHERE well_id = %s ORDER BY depth_start_md_m ASC",
                (well_id,),
            )
            return cur.fetchall()

    def for_wells(self, well_ids: list[str]) -> list[dict[str, Any]]:
        """DB-backed equivalent of NWISDataStore.get_events_for_top_wells —
        used by /corridors and /ahead_of_bit for their top-N offset wells'
        combined event set."""
        if not well_ids:
            return []
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"SELECT {self._COLUMNS} FROM drilling_events WHERE well_id = ANY(%s) ORDER BY well_id, depth_start_md_m ASC",
                (well_ids,),
            )
            return cur.fetchall()

    def all_events(self) -> list[dict[str, Any]]:
        """Every event in the canonical table — DB-backed equivalent of
        NWISDataStore.all_events, used by /events and /events/search.
        Structured filtering (hazard_type/formation/severity/depth) and
        facet computation stay in server.py's existing
        _filter_events_structured/_compute_facets, applied identically to
        whichever list (memory- or DB-sourced) this returns — not
        duplicated here as a second, potentially-diverging SQL filter."""
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(f"SELECT {self._COLUMNS} FROM drilling_events ORDER BY well_id, depth_start_md_m ASC")
            return cur.fetchall()
