import { defineConfig, loadEnv, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';

// https://vitejs.dev/config/
//
// The existing services/api.ts clients call Module 01 and Module 02 directly
// using VITE_M01_API_BASE / VITE_M02_API_BASE. The spatial package instead
// uses same-origin /api requests so its credential stays on the dev server;
// that route is proxied to Module 02 below.

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

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backend = (env.SPATIAL_BACKEND_URL || env.NWIS_BACKEND_URL || env.VITE_M02_API_BASE || 'http://localhost:8012').trim();
  const authHeader = (env.SPATIAL_API_AUTH_HEADER || 'X-API-Key').trim();
  // The existing frontend's local .env names this value VITE_M02_API_KEY.
  // Read it here as a server-side proxy fallback so the spatial package's
  // same-origin requests receive the same configured credential.
  const authValue = env.SPATIAL_API_AUTH_VALUE || env.SPATIAL_API_KEY || env.NWIS_API_KEY || env.VITE_M02_API_KEY || '';

  return {
    plugins: [react(), landingPageAtRoot()],
    resolve: { dedupe: ['react', 'react-dom'] },
    define: { CESIUM_BASE_URL: JSON.stringify('/cesiumStatic/') },
    server: {
      port: 5173,
      strictPort: true,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: backend,
          changeOrigin: true,
          secure: false,
          configure(proxy) {
            proxy.on('proxyReq', (proxyReq) => {
              proxyReq.removeHeader(authHeader);
              if (authValue) proxyReq.setHeader(authHeader, authValue);
            });
          },
        },
      },
    },
  };
});
