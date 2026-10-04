/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the ONE unified backend (Backend/run.py), default http://localhost:8000. Serves /api/v1 (documents), /api/v2 (wells/NWIS), /api/v3 (physics + predictive) and /api/evidence. */
  readonly VITE_API_BASE?: string;
  /** Must match NWIS_API_KEY in Backend/.env. Leave empty if the backend runs with auth disabled. */
  readonly VITE_API_KEY?: string;
  /** Optional override for the physics telemetry WebSocket (default: ws(s) form of VITE_API_BASE + /api/v3/physics/stream). */
  readonly VITE_TELEMETRY_WS_URL?: string;
  /** Optional override for the PDF evidence endpoint (default: VITE_API_BASE + /api/evidence). */
  readonly VITE_EVIDENCE_SERVER?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
