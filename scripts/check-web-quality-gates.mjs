import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const root = process.cwd();
const failures = [];
const maxRouteGzipBytes = 180 * 1024;

const e2ePath = join(root, "apps/web/tests/e2e/runtime-smoke.spec.ts");
const e2eSource = readFileSync(e2ePath, "utf8");
if (!e2eSource.includes("@axe-core/playwright") || !e2eSource.includes("analyze()")) {
  failures.push("apps/web e2e must run axe checks through @axe-core/playwright.");
}
if (!e2eSource.includes("toHaveScreenshot")) {
  failures.push("apps/web e2e must include a Playwright visual-regression assertion.");
}

const statsPath = join(root, "apps/web/.next/diagnostics/route-bundle-stats.json");
if (!existsSync(statsPath)) {
  failures.push("Next route bundle stats missing; run pnpm --filter @ai-desk/web build first.");
} else {
  const routeStats = JSON.parse(readFileSync(statsPath, "utf8"));
  for (const route of routeStats) {
    const chunkPaths = Array.isArray(route.firstLoadChunkPaths) ? route.firstLoadChunkPaths : [];
    let gzipBytes = 0;
    for (const chunkPath of chunkPaths) {
      const absoluteChunkPath = join(root, "apps/web", chunkPath);
      if (existsSync(absoluteChunkPath)) {
        gzipBytes += gzipSync(readFileSync(absoluteChunkPath)).length;
      }
    }
    if (gzipBytes > maxRouteGzipBytes) {
      failures.push(
        `${route.route} first-load gzip budget ${gzipBytes} exceeds ${maxRouteGzipBytes}.`,
      );
    }
  }
}

if (failures.length) {
  console.error("Web quality gate violations:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

process.stdout.write("Web quality gates OK.\n");
