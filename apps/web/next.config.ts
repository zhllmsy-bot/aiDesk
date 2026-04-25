import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  transpilePackages: [
    "@ai-desk/contracts-api",
    "@ai-desk/contracts-projects",
    "@ai-desk/contracts-runtime",
    "@ai-desk/contracts-execution",
    "@ai-desk/ui",
  ],
  turbopack: {
    root: path.resolve(__dirname, "../.."),
  },
};

export default nextConfig;
