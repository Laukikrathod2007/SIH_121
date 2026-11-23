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
// "/" is now the React app's /story (the product story is the landing
// page); the old static marketing page is no longer served. /benchmarks
// stays a static page (linked from the docs).
const STATIC_PAGES: Record<string, string> = {
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
//
// 2026-11: the product story (/story, React) replaced the static page as
// the landing page, so dist/index.html stays the React shell (React Router
// renders the story at "/"). The shell is also written to dist/app.html,
// so the existing /app, /docs, /film and /story rewrites keep working.
// The old static landing page (public/landing/index.html) was removed;
// public/landing/ still holds benchmarks.html and shared assets (including
// the BHA model the story's borehole loads).
function appShellAsIndex(): Plugin {
  return {
    name: 'app-shell-as-index',
    apply: 'build',
    closeBundle() {
      const dist = path.resolve(__dirname, 'dist');
      const spaShell = path.join(dist, 'index.html');
      if (!fs.existsSync(spaShell)) return;
      fs.copyFileSync(spaShell, path.join(dist, 'app.html'));
    },
  };
}

export default defineConfig({
  plugins: [react(), landingPageAtRoot(), appShellAsIndex()],
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-three': ['three', '@react-three/fiber', '@react-three/drei'],
          'vendor-leaflet': ['leaflet', 'react-leaflet'],
          'vendor-recharts': ['recharts'],
          'vendor-pdf': ['pdfjs-dist'],
          'vendor-katex': ['katex'],
        },
      },
    },
  },
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
