import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `BASE_PATH` is set by the GitHub Actions deploy workflow to `/${repo}/`.
// Locally, defaults to "/".
export default defineConfig({
  plugins: [react()],
  base: process.env.BASE_PATH ?? "/",
  build: {
    outDir: "dist",
    sourcemap: true,
  },
  server: {
    port: 5173,
  },
});
