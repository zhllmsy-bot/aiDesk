import path from "node:path";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  transpilePackages: [
    "@ai-desk/contracts-api",
    "@ai-desk/contracts-projects",
    "@ai-desk/contracts-runtime",
    "@ai-desk/contracts-execution",
  ],
  turbopack: {
    root: path.resolve(__dirname, "../.."),
  },
};

export default withNextIntl(nextConfig);
