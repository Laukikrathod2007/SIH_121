import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,   // never drift to 5174 — WS proxy would break
    host: '0.0.0.0',
    proxy: {
      // REST API
      '/api': {
        target: 'http://127.0.0.1:8008',
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
