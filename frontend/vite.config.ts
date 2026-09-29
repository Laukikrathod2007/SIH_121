import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
//
// No dev-server proxy: services/api.ts talks directly to our two real
// backends by absolute base URL (VITE_M01_API_BASE / VITE_M02_API_BASE,
// defaulting to http://localhost:8001 and http://localhost:8012) rather than
// a single proxied '/api' path to one backend on 8008 (Prasad's original
// setup). Both modules/01_document_intelligence/api/server.py and
// modules/02_nwis_backend/server.py already allow CORS from
// http://localhost:5173 by default (see their `_default_origins`), so no
// proxy is needed for local dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    host: '0.0.0.0',
  },
});
