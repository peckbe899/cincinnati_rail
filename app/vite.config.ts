// Vite builds the app into app/dist, which the hub serves (crhub serve never runs npm, 9.22). In development,
// `npm run dev -w app` proxies /api to a running hub on 127.0.0.1:8766.

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const hub = process.env.CRHUB_URL ?? "http://127.0.0.1:8766";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "dist",
    target: "es2023",
    sourcemap: true,
    emptyOutDir: true,
    // MapLibre is one big lazy chunk of its own; the first chunk is checked by scripts/check_size.ts.
    chunkSizeWarningLimit: 1600,
  },
  worker: { format: "es" },
  server: {
    port: 5173,
    strictPort: false,
    proxy: { "/api": { target: hub, changeOrigin: false } },
  },
  preview: { port: 4173 },
});
