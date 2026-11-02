// The built files go to frontend/dist and are served by Django under /static/
// (config/settings.py STATICFILES_DIRS), so reviewers need only Python.
// For UI work, `npm run dev` serves on :5173 and passes /api to Django on :8000.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? "/static/" : "/",
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
}));
