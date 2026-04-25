import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  esbuild: {
    jsx: "automatic",
    jsxImportSource: "react",
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: [
      "tests/unit/**/*.test.ts",
      "tests/unit/**/*.test.tsx",
      "features/**/*.test.ts",
      "features/**/*.test.tsx",
    ],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname),
      "@ai-desk/contracts-api": path.resolve(
        __dirname,
        "../../packages/contracts/api/src/index.ts",
      ),
    },
  },
});
