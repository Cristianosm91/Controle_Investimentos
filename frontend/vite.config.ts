import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    watch: {
      ignored: [
        "**/node_modules/**",
        "**/.git/**",
        "**/.e2e-dados/**",
        "**/playwright-report/**",
        "**/test-results/**",
        "**/dist/**",
      ],
    },
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
