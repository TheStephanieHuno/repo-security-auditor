// Vitest configuration for Repo Security Auditor.
// Phase A tests cover pure TypeScript service functions only (no JSX rendering).

import { defineConfig } from "vitest/config"
import path from "path"

export default defineConfig({
  test: {
    environment: "happy-dom",
    globals: true,
    testTimeout: 15000,
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
