import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // Credentials are deliberately unprefixed: Vite only exposes VITE_* values
  // to browser code. A host can use the generic SPATIAL_* variables, while the
  // existing NWIS_* names remain supported for this project's backend.
  const env = loadEnv(mode, process.cwd(), '');
  // Require an explicit backend address. Never silently attach to a stale port.
  const target = (env.SPATIAL_BACKEND_URL || env.NWIS_BACKEND_URL)?.trim();
  const authHeader = env.SPATIAL_API_AUTH_HEADER?.trim() || 'X-API-Key';
  const authValue = env.SPATIAL_API_AUTH_VALUE || env.SPATIAL_API_KEY || env.NWIS_API_KEY;
  const proxy = target ? {
    '/api': {
      target,
      changeOrigin: true,
      secure: false,
      configure(proxyServer) {
        proxyServer.on('proxyReq', (proxyReq) => {
          proxyReq.removeHeader(authHeader);
          if (authValue) proxyReq.setHeader(authHeader, authValue);
        });
      },
    },
  } : undefined;
  return {
    plugins: [react()],
    define: {
      CESIUM_BASE_URL: JSON.stringify('/cesiumStatic/'),
    },
    server: { port: Number(env.VITE_DEV_PORT) || 5173, strictPort: false, ...(proxy ? { proxy } : {}) },
    preview: { ...(proxy ? { proxy } : {}) },
    build: { rollupOptions: { output: { manualChunks(id) {
      if (id.includes('/node_modules/three/')) return 'three-core';
      if (id.includes('/node_modules/@react-three/fiber/')) return 'react-three-fiber';
      if (id.includes('/node_modules/@react-three/drei/')) return 'react-three-tools';
      return undefined;
    } } } },
  };
});
