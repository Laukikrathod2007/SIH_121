-- =============================================================================
-- eRTMAC-NWIS (SIH 26121) — Database Layer
-- schema.sql
--
-- A PostgreSQL schema modeled on the three real industry-converging
-- standards for subsurface/drilling data:
--   - PPDM  (Professional Petroleum Data Management)  -> master/reference data
--   - WITSML (Wellsite Information Transfer Standard)  -> work-product (drilling) data
--   - OSDU  (Open Subsurface Data Universe)             -> the master / work-product /
--            derived three-tier separation this file is organized around
--
-- Grounded directly in the REAL Pydantic models already shipping in:
--   modules/01_document_intelligence/models/schemas.py
--   modules/02_nwis_backend/models/schemas.py
--   modules/02_nwis_backend/search/knowledge_search.py   (embedding dims/text)
--   modules/02_nwis_backend/engines/dors_engine.py        (spatial scoring, formation groups)
--   modules/02_nwis_backend/engines/stratigraphic_correlator.py (trajectory access pattern)
--   modules/05_predictive_analytics/predictive/alert_advisory_engine.py (ActiveAlert)
--
-- No field names below are invented without a source comment pointing at the
-- Pydantic model / engine they came from.
--
-- This schema is a NEW, standalone layer. It does not replace or get wired
-- into modules 01/02's existing SQLite/JSON storage — see README.md's
-- "Migration path" section.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- =============================================================================
-- TIER 1 — MASTER / REFERENCE DATA (PPDM-style)
-- Slowly-changing, authoritative lookup entities that everything else hangs
-- off. This is the layer PPDM calls "business associate" / "field" / "well"
-- master tables.
-- =============================================================================

CREATE TABLE operators (
    operator_id     SERIAL PRIMARY KEY,
    -- matches Well.operator string values seen in data/synthetic/wells.json
    -- ("OIL_INDIA_LIMITED", "ONGC")
    operator_code   TEXT NOT NULL UNIQUE,
    operator_name   TEXT NOT NULL,
    country         TEXT NOT NULL DEFAULT 'India',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE fields (
    field_id        SERIAL PRIMARY KEY,
    -- models/schemas.py Well.field_code / Well.field (module 02)
    field_code      TEXT NOT NULL UNIQUE,
    field_name      TEXT NOT NULL UNIQUE,
    operator_id     INT REFERENCES operators(operator_id),
    basin           TEXT DEFAULT 'Assam-Arakan Basin',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Reference stratigraphic column. Distinct from formation_tops (Tier 2):
-- this is the master list of formation NAMES and which structural group
-- they belong to, mirroring dors_engine.py's ASSAM_FORMATION_GROUPS dict
-- (used by score_formation() to grant partial credit for "adjacent
-- formation in same stratigraphic group"). formation_tops rows carry the
-- per-well extracted top/base depths and optionally link back here.
CREATE TABLE formations (
    formation_id        SERIAL PRIMARY KEY,
    formation_name       TEXT NOT NULL UNIQUE,
    -- engines/dors_engine.py ASSAM_FORMATION_GROUPS keys:
    -- UPPER_ASSAM / BARAIL / EOCENE / BASEMENT
    stratigraphic_group  TEXT NOT NULL,
    typical_lithology    TEXT,
    display_order        INT,       -- shallow -> deep, for stratigraphic-column UIs
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- models/schemas.py (module 02) HazardType enum — the 6 values exactly.
CREATE TABLE hazard_type (
    code            TEXT PRIMARY KEY,
    description     TEXT NOT NULL
);

INSERT INTO hazard_type (code, description) VALUES
    ('MUD_LOSS',              'Loss of drilling fluid circulation into the formation'),
    ('STUCK_PIPE',            'Drillstring becomes immobilized in the wellbore'),
    ('KICK',                  'Uncontrolled formation fluid influx into the wellbore'),
    ('WELLBORE_INSTABILITY',  'Hole enlargement / collapse (e.g. washout, sloughing shale)'),
    ('TORQUE_SPIKE',          'Abnormal torque response indicating mechanical drag/friction'),
    ('CEMENTING_FAILURE',     'Cement job failed to achieve zonal isolation / bond');

CREATE TABLE wells (
    -- Business key used verbatim by both modules' JSON/API payloads
    -- (Well.well_id, e.g. "WELL-NHK-001"). Kept as the primary key rather
    -- than introducing a surrogate UUID so this schema is directly loadable
    -- from, and directly joinable against, the existing services without an
    -- ID-mapping layer. witsml_uid below is the *separate* real UUID field
    -- Well already carries (Well.witsml_uid).
    well_id             TEXT PRIMARY KEY,
    well_name           TEXT NOT NULL,
    field_id            INT REFERENCES fields(field_id),
    operator_id         INT REFERENCES operators(operator_id),
    -- Well.surface_lat / Well.surface_lon, stored as real PostGIS geography
    -- instead of raw float columns — this is what lets a GiST spatial index
    -- replace the ad hoc haversine_km() float math in dors_engine.py's
    -- score_spatial().
    surface_location    geography(Point, 4326) NOT NULL,
    kb_elevation_m       NUMERIC NOT NULL DEFAULT 10.0,
    total_depth_md_m     NUMERIC NOT NULL,
    well_type            TEXT NOT NULL DEFAULT 'Vertical'
                          CHECK (well_type IN ('Vertical','J-Type','S-Type','Horizontal')),
    spud_date             DATE,
    completion_date       DATE,
    status                TEXT NOT NULL DEFAULT 'COMPLETED'
                          CHECK (status IN ('PRODUCING','COMPLETED','ABANDONED','SUSPENDED','DRILLING')),
    witsml_uid            UUID NOT NULL DEFAULT gen_random_uuid(),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_wells_surface_location ON wells USING GIST (surface_location);
CREATE INDEX idx_wells_field ON wells (field_id);
CREATE INDEX idx_wells_operator ON wells (operator_id);

-- =============================================================================
-- PROVENANCE LAYER
-- Mirrors module 01's "zero hallucination" review workflow
-- (models/schemas.py DocumentExtractionResult + api/routes/review.py) so any
-- Tier-2 row extracted from a document can be traced back to it, and that
-- document's human-curation state travels with it.
-- =============================================================================

CREATE TABLE documents (
    -- module 01: DocumentExtractionResult.document_id ("DOC-XXXXXXXXXXXX")
    document_id                   TEXT PRIMARY KEY,
    job_id                        TEXT,
    source_filename               TEXT NOT NULL,
    document_type                 TEXT DEFAULT 'UNKNOWN'
                                   CHECK (document_type IN
                                       ('DAILY_DRILLING_REPORT','WELL_COMPLETION_REPORT',
                                        'MUD_LOG','MORNING_REPORT','UNKNOWN')),
    well_id                       TEXT REFERENCES wells(well_id),  -- resolved link, nullable
    well_name                     TEXT,   -- raw extracted well name (may not resolve to a well_id)
    operator                      TEXT,
    report_date                   DATE,
    total_pages                   INT DEFAULT 0,
    pages_processed               INT DEFAULT 0,
    scanned_pages                 INT DEFAULT 0,
    template_used                 TEXT,
    extraction_started_at         TIMESTAMPTZ,
    extraction_completed_at       TIMESTAMPTZ,
    total_processing_time_ms      NUMERIC,
    cloud_fallback_pages_count    INT DEFAULT 0,
    cloud_fallback_providers_used TEXT[] DEFAULT '{}',
    total_npt_hours               NUMERIC DEFAULT 0,
    validation_status             TEXT DEFAULT 'PASS'
                                   CHECK (validation_status IN
                                       ('PASS','FLAGGED_LOW_CONFIDENCE',
                                        'FAILED_PHYSICS_VALIDATION','PENDING_MANUAL_REVIEW')),
    overall_confidence             NUMERIC(5,4),
    flagged_fields_count           INT DEFAULT 0,
    physics_violations_count       INT DEFAULT 0,
    witsml_compliant                BOOLEAN DEFAULT TRUE,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_documents_well ON documents (well_id);

-- Mirrors DocumentExtractionResult's review fields EXACTLY (same names) —
-- see models/schemas.py lines ~413-425 and api/routes/review.py.
CREATE TABLE document_review (
    document_id       TEXT PRIMARY KEY REFERENCES documents(document_id) ON DELETE CASCADE,
    reviewed           BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_by         TEXT,
    reviewed_at          TIMESTAMPTZ,
    review_decision       TEXT CHECK (review_decision IN ('approved','rejected')),
    review_notes           TEXT,
    -- list of {field_path, note, annotated_by, annotated_at} — same shape as
    -- api/routes/review.py's FieldAnnotation, deliberately NOT a machine
    -- patch of the extracted value (see that file's module docstring).
    field_annotations       JSONB NOT NULL DEFAULT '[]'::jsonb
);

-- =============================================================================
-- TIER 2 — WORK-PRODUCT DATA (WITSML-style)
-- Extracted / surveyed / measured facts about a specific well. Every table
-- here that can trace to a source document carries source_document_id /
-- source_page / extraction_confidence (module 01's ExtractedField provenance
-- triad, flattened onto the row instead of a nested object per field).
-- =============================================================================

-- One row per directional-survey station, not a single LINESTRING per well.
-- Chosen deliberately: engines/stratigraphic_correlator.py and
-- engines/dors_engine.py both walk trajectories station-by-station
-- (tvd_at_md/inclination_at_md/azimuth_at_md all loop `for i in
-- range(1, len(stations))` bracketing target_md between two adjacent
-- SurveyStation rows, and score_trajectory samples 10 points along that same
-- station list) — i.e. the application's real access pattern is
-- "interpolate between the station immediately above/below a given MD", not
-- "give me the whole curve as one geometry". A point-per-station table with
-- an MD index matches that pattern directly; a single LINESTRINGZ would
-- require unpacking via ST_DumpPoints for every such lookup. The geography
-- point is still provided per station (for map/3D rendering, GiST queries,
-- ST_MakeLine() aggregation on demand) — this gets both access patterns
-- without forcing the hot path through geometry unpacking.
CREATE TABLE trajectory_stations (
    station_id           BIGSERIAL PRIMARY KEY,
    well_id                TEXT NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    -- models/schemas.py (module 02) SurveyStation — every field verbatim
    md_m                    NUMERIC NOT NULL,
    inclination_deg          NUMERIC NOT NULL,
    azimuth_deg                NUMERIC NOT NULL,
    tvd_m                      NUMERIC NOT NULL,
    ns_m                        NUMERIC NOT NULL,
    ew_m                          NUMERIC NOT NULL,
    tvdss_m                        NUMERIC NOT NULL,
    method                          TEXT DEFAULT 'MINIMUM_CURVATURE',  -- WellTrajectory.method
    -- geography(PointZ): lon/lat computed from the well's surface_location
    -- offset by ns_m/ew_m (local equirectangular approximation — consistent
    -- with dors_engine.py's own haversine spherical-earth approximation
    -- elsewhere in this codebase); Z is TVD in metres (positive-down
    -- drilling convention, not a geodetic elevation).
    station_location                 geography(PointZ, 4326),
    source_document_id                 TEXT REFERENCES documents(document_id),
    source_page                          INT,
    extraction_confidence                 NUMERIC(5,4),
    UNIQUE (well_id, md_m)
);

CREATE INDEX idx_trajectory_stations_well_md ON trajectory_stations (well_id, md_m);
CREATE INDEX idx_trajectory_stations_location ON trajectory_stations USING GIST (station_location);

CREATE TABLE formation_tops (
    top_id                  BIGSERIAL PRIMARY KEY,
    well_id                   TEXT NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    -- models/schemas.py (module 02) FormationTop — verbatim field names
    formation_name              TEXT NOT NULL,
    formation_id                  INT REFERENCES formations(formation_id),  -- best-effort link to master list
    top_md_m                        NUMERIC NOT NULL,
    top_tvd_m                         NUMERIC NOT NULL,
    base_md_m                           NUMERIC NOT NULL,
    thickness_m                           NUMERIC,
    pore_pressure_gradient_ppg              NUMERIC DEFAULT 9.0,
    lithology                                 TEXT,
    confidence                                  NUMERIC(5,4) DEFAULT 0.90,
    source_document_id                            TEXT REFERENCES documents(document_id),
    source_page                                     INT,
    extraction_confidence                             NUMERIC(5,4)
);

CREATE INDEX idx_formation_tops_well ON formation_tops (well_id);
CREATE INDEX idx_formation_tops_well_depth ON formation_tops (well_id, top_md_m, base_md_m);
CREATE INDEX idx_formation_tops_formation ON formation_tops (formation_id);

CREATE TABLE drilling_events (
    -- models/schemas.py (module 02) DrillingEvent.event_id default factory
    -- produces "EVT-XXXXXXXX" (8 hex chars) — a TEXT business key, not a
    -- UUID. (See README's "judgment calls" section: the task brief's
    -- illustrative `event_id uuid` is adjusted to TEXT here to match the
    -- real generated IDs so event_embeddings can actually FK to them.)
    event_id                TEXT PRIMARY KEY,
    well_id                    TEXT NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    event_type                    TEXT NOT NULL REFERENCES hazard_type(code),
    severity                        TEXT NOT NULL DEFAULT 'MEDIUM'
                                     CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    depth_start_md_m                  NUMERIC NOT NULL,
    depth_end_md_m                      NUMERIC,
    formation                             TEXT,
    formation_id                            INT REFERENCES formations(formation_id),
    raw_narrative                             TEXT NOT NULL DEFAULT '',
    npt_hours                                   NUMERIC DEFAULT 0.0,
    iadc_npt_code                                 TEXT,
    loss_rate_bbl_hr                                NUMERIC,
    mitigation_description                            TEXT,
    outcome                                             TEXT,
    confidence                                            NUMERIC(5,4) DEFAULT 0.90,
    witsml_mapping                                          TEXT DEFAULT 'opsReport.activity (WITSML 2.0)',
    source_document_id                                        TEXT REFERENCES documents(document_id),
    source_page                                                 INT,
    extraction_confidence                                         NUMERIC(5,4),
    created_at                                                      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_drilling_events_well ON drilling_events (well_id);
CREATE INDEX idx_drilling_events_well_depth ON drilling_events (well_id, depth_start_md_m);
CREATE INDEX idx_drilling_events_type ON drilling_events (event_type);
-- GIN full-text index on raw_narrative — complements (does not replace) the
-- pgvector semantic search over the same underlying text in
-- search/knowledge_search.py's _searchable_text(): a keyword/phrase fallback
-- and an exact-substring safety net for when semantic recall misses.
CREATE INDEX idx_drilling_events_narrative_fts
    ON drilling_events USING GIN (to_tsvector('english', raw_narrative));

CREATE TABLE npt_records (
    -- module 01: models/schemas.py NPTRecord has no id field of its own
    -- (it's a nested list item on PageExtractionResult) — bigserial here.
    npt_id                  BIGSERIAL PRIMARY KEY,
    well_id                    TEXT REFERENCES wells(well_id) ON DELETE CASCADE,  -- nullable: NPTRecord itself carries no well_id
    event_id                     TEXT REFERENCES drilling_events(event_id),        -- optional link if this NPT line corresponds to a normalized event
    iadc_code                      TEXT,
    description                      TEXT NOT NULL,
    start_time_hhmm                    TEXT,
    end_time_hhmm                        TEXT,
    npt_hours                              NUMERIC,
    depth_md_m                               NUMERIC,
    cost_usd_estimate                          NUMERIC,
    source_document_id                           TEXT REFERENCES documents(document_id),
    source_page                                    INT,
    extraction_confidence                            NUMERIC(5,4)
);

CREATE INDEX idx_npt_records_well ON npt_records (well_id);
CREATE INDEX idx_npt_records_document ON npt_records (source_document_id);

CREATE TABLE mud_properties (
    -- module 01: models/schemas.py MudProperties — page/document-scoped
    -- (no well_id field on the Pydantic model itself), so well_id here is a
    -- resolved enrichment column, nullable.
    mud_id                   BIGSERIAL PRIMARY KEY,
    well_id                     TEXT REFERENCES wells(well_id) ON DELETE CASCADE,
    source_document_id             TEXT REFERENCES documents(document_id),
    source_page                      INT,
    mud_weight_ppg                     NUMERIC,
    funnel_viscosity_sec                 NUMERIC,
    plastic_viscosity_cp                   NUMERIC,
    yield_point_lbf_100sqft                  NUMERIC,
    water_loss_ml_30min                        NUMERIC,
    cake_thickness_mm                            NUMERIC,
    chloride_content_ppm                           NUMERIC,
    ph                                               NUMERIC,
    extraction_confidence                              NUMERIC(5,4),
    recorded_at                                          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_mud_properties_well ON mud_properties (well_id);

-- TimescaleDB hypertable. models/schemas.py (module 02) TelemetryRecord —
-- verbatim fields. `time` (parsed from TelemetryRecord.timestamp, an ISO8601
-- string) is the hypertable partitioning column, so it's part of the PK
-- (TimescaleDB requires any uniqueness constraint to include the
-- partitioning column).
CREATE TABLE telemetry_records (
    time                       TIMESTAMPTZ NOT NULL,
    well_id                      TEXT NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    depth_m                        NUMERIC NOT NULL,
    rop_m_hr                         NUMERIC DEFAULT 0.0,
    wob_klbs                           NUMERIC DEFAULT 0.0,
    rpm                                  NUMERIC DEFAULT 0.0,
    torque_kn_m                            NUMERIC DEFAULT 0.0,
    standpipe_pressure_psi                   NUMERIC DEFAULT 0.0,
    flow_in_lpm                                NUMERIC DEFAULT 0.0,
    flow_out_lpm                                 NUMERIC DEFAULT 0.0,
    pit_volume_bbl                                 NUMERIC DEFAULT 0.0,
    mud_weight_ppg                                   NUMERIC DEFAULT 9.0,
    d_exponent                                         NUMERIC DEFAULT 1.0,
    PRIMARY KEY (well_id, time)
);

SELECT create_hypertable('telemetry_records', by_range('time'), if_not_exists => TRUE);
CREATE INDEX idx_telemetry_well_time ON telemetry_records (well_id, time DESC);

-- =============================================================================
-- TIER 3 — DERIVED / OUR-OWN-IP DATA
-- Nothing here is a raw measurement or a raw extraction; every row is
-- computed by this project's own engines (DORS, Risk Corridor, 4-Pillar
-- Confidence, Alert Advisory) from Tier-1/Tier-2 data.
-- =============================================================================

CREATE TABLE risk_corridors (
    -- models/schemas.py (module 02) RiskCorridor.corridor_id default
    -- factory: "COR-XXXXXX" (6 hex chars) — TEXT business key.
    corridor_id             TEXT PRIMARY KEY,
    active_well_id             TEXT REFERENCES wells(well_id),
    hazard_type                  TEXT NOT NULL REFERENCES hazard_type(code),
    depth_start_m                  NUMERIC NOT NULL,
    depth_end_m                      NUMERIC NOT NULL,
    -- RiskCorridor.contributing_wells / contributing_events are List[str] of
    -- well_id / event_id business keys. Stored as native arrays rather than
    -- a join table: judgment call — this is derived/IP output regenerated
    -- wholesale by the engine on every run, not master data with its own
    -- independent lifecycle, so the normalization cost of a join table buys
    -- little here (see README "judgment calls").
    contributing_wells               TEXT[] NOT NULL DEFAULT '{}',
    contributing_events                TEXT[] NOT NULL DEFAULT '{}',
    event_count                          INT NOT NULL DEFAULT 0,
    avg_npt_hours                          NUMERIC,
    max_severity                             TEXT,
    historical_frequency                       NUMERIC CHECK (historical_frequency BETWEEN 0 AND 1),
    lead_distance_m                              NUMERIC,
    proximity_risk_level                           TEXT NOT NULL DEFAULT 'LOW'
                                                    CHECK (proximity_risk_level IN ('LOW','MODERATE','HIGH','CRITICAL')),
    recommended_action                               TEXT DEFAULT '',
    formation                                          TEXT,
    formation_id                                         INT REFERENCES formations(formation_id),
    created_at                                             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_risk_corridors_well ON risk_corridors (active_well_id);
CREATE INDEX idx_risk_corridors_hazard ON risk_corridors (hazard_type);
CREATE INDEX idx_risk_corridors_depth ON risk_corridors (depth_start_m, depth_end_m);

CREATE TABLE hazard_assessments (
    assessment_id             BIGSERIAL PRIMARY KEY,   -- HazardRiskAssessment has no id field itself; one row per (well, hazard_type, assessed_at)
    well_id                     TEXT NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    current_depth_m               NUMERIC,
    hazard_type                     TEXT NOT NULL REFERENCES hazard_type(code),
    risk_level                        TEXT NOT NULL CHECK (risk_level IN ('LOW','MODERATE','HIGH','CRITICAL')),
    composite_score                     NUMERIC(6,4) NOT NULL,   -- R_H(t)
    p_history                             NUMERIC(6,4) NOT NULL,   -- alpha=0.45
    a_sensor                                NUMERIC(6,4) NOT NULL,   -- beta=0.35
    m_ml                                      NUMERIC(6,4) NOT NULL,   -- gamma=0.20
    -- HazardRiskAssessment.m_ml_source: "trained_model" | "heuristic_fallback"
    m_ml_source                                 TEXT NOT NULL DEFAULT 'heuristic_fallback'
                                                 CHECK (m_ml_source IN ('trained_model','heuristic_fallback')),
    -- FourPillarConfidence, flattened onto the row (chosen over a nested
    -- JSONB blob because evidence_strength/audit_status are exactly the
    -- kind of thing a reviewer/judge will want to filter/aggregate on).
    evidence_strength                             TEXT CHECK (evidence_strength IN ('HIGH','MODERATE','LOW','INSUFFICIENT')),
    evidence_count                                  INT,
    sensor_anomaly_score                              NUMERIC(6,4),
    data_quality_index                                  NUMERIC(6,4),
    audit_status                                          TEXT DEFAULT 'GROUNDED',
    overall_confidence                                      NUMERIC(6,4),
    active_corridor_id                                        TEXT REFERENCES risk_corridors(corridor_id),
    lead_time_meters                                            NUMERIC,
    recommended_action                                            TEXT DEFAULT '',
    evidence_events                                                 TEXT[] NOT NULL DEFAULT '{}',  -- event_ids
    assessed_at                                                       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_hazard_assessments_well ON hazard_assessments (well_id, assessed_at DESC);
CREATE INDEX idx_hazard_assessments_hazard ON hazard_assessments (hazard_type);

-- Grounded on modules/05_predictive_analytics/predictive/alert_advisory_engine.py
-- ActiveAlert (+ its embedded MitigationAction) — field names verbatim.
CREATE TABLE alerts (
    alert_id                  TEXT PRIMARY KEY,   -- ActiveAlert.alert_id
    well_id                     TEXT NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    hazard_type                  TEXT REFERENCES hazard_type(code),
    severity                       TEXT NOT NULL CHECK (severity IN ('CRITICAL','WARNING','ADVISORY','CLEARED')),
    score                             NUMERIC(6,4),
    confidence                         NUMERIC(6,4),
    trigger_reason                       TEXT,
    evidence_chain                         TEXT[] NOT NULL DEFAULT '{}',
    -- ActiveAlert.recommended_mitigation is a single embedded MitigationAction
    -- value object (action_id/hazard_type/title/description/
    -- parameter_adjustments/applied/applied_at) — judgment call: stored as
    -- JSONB rather than a separate table since it's owned 1:1 by the alert
    -- and never queried independently (see README "judgment calls").
    recommended_mitigation                   JSONB,
    status                                      TEXT NOT NULL DEFAULT 'ACTIVE'
                                                 CHECK (status IN ('ACTIVE','ACKNOWLEDGED','MITIGATED','CLEARED')),
    triggered_at                                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                                      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_alerts_well ON alerts (well_id, triggered_at DESC);
CREATE INDEX idx_alerts_status ON alerts (status);

-- Versioned ML model metadata for modules/05_predictive_analytics's trained
-- classifiers (e.g. data/models/{kick,stuck_pipe,wellbore_instability}_model.joblib
-- referenced by HazardRiskAssessment.m_ml_source == "trained_model").
CREATE TABLE model_registry (
    model_id                   TEXT PRIMARY KEY,     -- e.g. "kick_model_v1"
    model_name                   TEXT NOT NULL,         -- e.g. "kick_model"
    hazard_type                    TEXT REFERENCES hazard_type(code),
    version                           TEXT NOT NULL DEFAULT 'v1',
    algorithm                          TEXT,
    source_module                        TEXT DEFAULT '05_predictive_analytics',
    artifact_path                          TEXT,        -- e.g. modules/02_nwis_backend/data/models/kick_model.joblib
    training_sample_count                    INT,
    metrics                                    JSONB NOT NULL DEFAULT '{}'::jsonb,  -- precision/recall/f1/auc...
    feature_list                                 JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active                                      BOOLEAN NOT NULL DEFAULT TRUE,
    trained_at                                       TIMESTAMPTZ,
    created_at                                         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_model_registry_hazard ON model_registry (hazard_type);

-- Semantic search over drilling_events. 384 dims because
-- search/knowledge_search.py's EMBEDDING_MODEL_NAME =
-- "all-MiniLM-L6-v2" (sentence-transformers), which is a 384-dimension
-- model — confirmed by that model's published config, and matches this
-- codebase's own model choice exactly (no dimension was invented).
CREATE TABLE event_embeddings (
    event_id        TEXT PRIMARY KEY REFERENCES drilling_events(event_id) ON DELETE CASCADE,
    embedding         vector(384) NOT NULL,
    model_name          TEXT NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    -- same text construction as search/knowledge_search.py's
    -- _searchable_text(): event_type + formation + raw_narrative +
    -- mitigation_description + outcome, space-joined.
    source_text_preview    TEXT,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW, cosine distance — matches _get_model()'s
-- `model.encode(..., normalize_embeddings=True)` + dot-product-as-cosine
-- pattern in knowledge_search.py, so query-time `<=>` (cosine distance)
-- operator ordering is directly comparable to that existing similarity score.
CREATE INDEX idx_event_embeddings_hnsw
    ON event_embeddings USING hnsw (embedding vector_cosine_ops);

-- =============================================================================
-- End of schema.sql
-- =============================================================================
