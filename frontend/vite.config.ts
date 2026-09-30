import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';

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

// Serves the static marketing landing page (public/landing/index.html) at
// the exact root path "/", while leaving every other path -- including
// "/app" and all its sub-routes -- to Vite's normal SPA fallback (which
// serves the React app's own index.html). Vite only has one built-in HTML
// entry, so without this the root path would always show the React shell
// instead of the static page. Only intercepts the exact "/" request; the
// React Router app itself is untouched.
function landingPageAtRoot(): Plugin {
  return {
    name: 'landing-page-at-root',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url === '/') {
          const landingHtml = fs.readFileSync(
            path.resolve(__dirname, 'public/landing/index.html'),
            'utf-8',
          );
          res.setHeader('Content-Type', 'text/html');
          res.end(landingHtml);
          return;
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), landingPageAtRoot()],
  server: {
    port: 5173,
    strictPort: true,
    host: '0.0.0.0',
  },
});
