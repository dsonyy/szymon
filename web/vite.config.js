import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
  },
  server: {
    proxy: {
      "/api": {
        target: "https://localhost:2137",
        secure: false,
      },
      "/health": {
        target: "https://localhost:2137",
        secure: false,
      },
    },
  },
});
