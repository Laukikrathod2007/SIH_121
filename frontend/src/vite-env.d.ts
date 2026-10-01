/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** modules/01_document_intelligence base URL, default http://localhost:8001 */
  readonly VITE_M01_API_BASE?: string;
  /** modules/02_nwis_backend base URL, default http://localhost:8012 */
  readonly VITE_M02_API_BASE?: string;
  /** modules/03_physics_engine placeholder base URL, default http://localhost:8003 — NOT YET WIRED, see services/api.ts */
  readonly VITE_M03_API_BASE?: string;
  /** Must match NWIS_API_KEY in modules/01_document_intelligence/.env */
  readonly VITE_M01_API_KEY?: string;
  /** Must match NWIS_API_KEY in modules/02_nwis_backend/.env */
  readonly VITE_M02_API_KEY?: string;
  /** Placeholder — module 03 has no auth wired up yet either */
  readonly VITE_M03_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
