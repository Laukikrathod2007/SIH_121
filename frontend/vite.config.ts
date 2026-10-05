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
          // The file's relative asset paths (href="assets/...", no leading
          // slash) are correct for its real location, /landing/, but it's
          // served here at a different path -- resolution is handled by the
          // <base href="/landing/"> the source file carries itself, so it
          // can be served verbatim in both dev and the production build
          // (see landingPageAtRootForBuild below).
          res.setHeader('Content-Type', 'text/html');
          res.setHeader('Cache-Control', 'no-store');
          res.end(landingHtml);
          return;
        }
        next();
      });
    },
  };
}

// Production counterpart to landingPageAtRoot() above. That plugin is
// dev-server-only (configureServer), so `vite build` emitted the React
// shell to dist/index.html and nothing served the landing page at "/".
// On Vercel that was unfixable from vercel.json alone: its router runs a
// "filesystem" phase BEFORE any rewrites, and "/" implicitly resolves to a
// root-level index.html when one exists -- so dist/index.html (the SPA)
// always won, and the explicit { "/" -> "/landing/index.html" } rewrite
// never got a chance to run. React then mounted, hit App.tsx's catch-all
// <Navigate to="/app">, and every visitor bounced past the landing page.
//
// Fix: after the build, make dist/index.html the LANDING page and move the
// React shell to dist/app.html. Now the filesystem phase serving "/" ->
// dist/index.html is exactly what we want, and /app* rewrites to app.html.
// Asset URLs in the built shell are absolute (/assets/...), so serving it
// from a different filename changes nothing about how it loads.
function landingPageAtRootForBuild(): Plugin {
  return {
    name: 'landing-page-at-root-build',
    apply: 'build',
    closeBundle() {
      const dist = path.resolve(__dirname, 'dist');
      const spaShell = path.join(dist, 'index.html');
      const landing = path.join(dist, 'landing', 'index.html');
      if (!fs.existsSync(spaShell) || !fs.existsSync(landing)) return;

      fs.renameSync(spaShell, path.join(dist, 'app.html'));
      // Copied verbatim: public/landing/index.html already carries its own
      // <base href="/landing/">, which is what makes its relative asset
      // URLs (href="assets/...") resolve correctly while it's served from
      // the root. No injection needed here (unlike the dev middleware
      // above, which reads the file straight off disk before that base tag
      // was added to the source).
      fs.copyFileSync(landing, spaShell);
    },
  };
}

export default defineConfig({
  plugins: [react(), landingPageAtRoot(), landingPageAtRootForBuild()],
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
