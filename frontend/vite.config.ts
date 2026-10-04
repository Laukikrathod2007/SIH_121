import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';

// https://vitejs.dev/config/
//
// Backend consolidation (2026-10-04): modules/01_document_intelligence
// (:8001), modules/02_nwis_backend (:8002), and modules/04_physics_engine+
// 05_predictive_analytics (:8003) were 3 independently-launched FastAPI
// processes; they're now ONE unified app (Backend/app/main.py, :8000 by
// default -- see services/api.ts). With exactly one real backend to talk
// to, a dev-server proxy is now the better default (previously
// deliberately omitted, when there were 2+ backends and no single thing to
// proxy to): it lets local dev be same-origin through Vite's dev server
// (CORS stops mattering in dev at all, not just allowed), and it mirrors
// how a real reverse-proxy deployment (nginx in front of both the static
// frontend build and the API) would actually look in production -- one
// step closer to "clean, easy to deploy." The production `dist/` build
// still uses VITE_API_BASE as an absolute URL (proxy only affects `vite
// dev`), so this is additive, not a replacement for that config.
const BACKEND_ORIGIN = process.env.VITE_API_BASE || 'http://localhost:8000';

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
    proxy: {
      '/api': { target: BACKEND_ORIGIN, changeOrigin: true },
      '/ws': { target: BACKEND_ORIGIN.replace(/^http/, 'ws'), ws: true, changeOrigin: true },
    },
  },
});
