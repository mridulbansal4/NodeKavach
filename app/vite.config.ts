import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Frontend runs on :3000 and proxies /api to the FastAPI backend on :8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
