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

// Serves static marketing pages (public/landing/*.html) at clean top-level
// paths -- "/" for index.html, "/benchmarks" for benchmarks.html -- while
// leaving every other path, including "/app" and all its sub-routes, to
// Vite's normal SPA fallback (which serves the React app's own index.html).
// Vite only has one built-in HTML entry, so without this these paths would
// always show the React shell instead of the static pages. Only intercepts
// these exact requests; the React Router app itself is untouched.
const STATIC_PAGES: Record<string, string> = {
  '/': 'index.html',
  '/benchmarks': 'benchmarks.html',
};

function landingPageAtRoot(): Plugin {
  return {
    name: 'landing-page-at-root',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const file = STATIC_PAGES[req.url ?? ''];
        if (file) {
          const landingHtml = fs.readFileSync(
            path.resolve(__dirname, 'public/landing', file),
            'utf-8',
          );
          // The file's own relative asset paths (href="assets/css/...", no
          // leading slash) are correct for its real location, /landing/ --
          // but it's being served here at a different path, so the browser
          // would resolve them against the wrong base and every
          // stylesheet/script/image 404s. Injecting <base href="/landing/">
          // fixes resolution without touching the file on disk at all.
          const withBase = landingHtml.replace(
            /<head>/i,
            '<head><base href="/landing/">',
          );
          res.setHeader('Content-Type', 'text/html');
          res.setHeader('Cache-Control', 'no-store');
          res.end(withBase);
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
