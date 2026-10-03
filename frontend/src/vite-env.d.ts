/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** modules/01_document_intelligence base URL, default http://localhost:8001 */
  readonly VITE_M01_API_BASE?: string;
  /** modules/02_nwis_backend base URL, default http://localhost:8002 */
  readonly VITE_M02_API_BASE?: string;
  /** modules/04_physics_engine base URL (also serves module 05's predictive code), default http://localhost:8003 — real server, but ML models are typically UNFITTED_FALLBACK on a fresh checkout (no trained .joblib artifacts); see services/api.ts and AUDIT/02_CORE_INTEGRATION.md */
  readonly VITE_M03_API_BASE?: string;
  /** Must match NWIS_API_KEY in modules/01_document_intelligence/.env */
  readonly VITE_M01_API_KEY?: string;
  /** Must match NWIS_API_KEY in modules/02_nwis_backend/.env */
  readonly VITE_M02_API_KEY?: string;
  /** Must match NWIS_API_KEY in modules/04_physics_engine/.env — auth IS enforced on every /api/v3 route except /health */
  readonly VITE_M03_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
