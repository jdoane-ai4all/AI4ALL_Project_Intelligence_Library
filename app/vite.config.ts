import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// `vite build --mode single` produces one self-contained index.html (used by the Streamlit wrapper).
export default defineConfig(({ mode }) => ({
  plugins: mode === "single" ? [react(), viteSingleFile()] : [react()],
  base: "./",
  build: mode === "single" ? { outDir: "dist-single", assetsInlineLimit: 100000000 } : {},
  server: { host: true, port: 5173 },
}));
