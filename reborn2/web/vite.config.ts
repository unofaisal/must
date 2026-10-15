import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import { fileURLToPath } from "node:url";

// In dev the page runs on :5173 and forwards /api to the FastAPI server on :8000.
// `npm run build` writes web/dist, which FastAPI serves at http://localhost:8000.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(path.dirname(fileURLToPath(import.meta.url)), "src") } },
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
