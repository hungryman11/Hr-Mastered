import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command }) => ({
  plugins: [react()],
  // Django serves production assets from /static/. Vite development must use
  // the site root so direct SPA requests such as /app/login and /app/callback
  // fall back to index.html instead of being treated as outside the base path.
  base: command === 'serve' ? '/' : '/static/',
  appType: 'spa',
  server: {
    host: 'localhost',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
}));
