import { execFileSync } from "node:child_process";
import { copyFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const fullOpenApiPath = join(root, "packages/contracts/api/openapi/full.openapi.json");
const fullSnapshotPath = join(root, "apps/api/tests/contracts_snapshots/openapi-full.json");
const controlPlaneOpenApiPath = join(
  root,
  "packages/contracts/projects/openapi/control-plane.openapi.json",
);

copyFileSync(fullOpenApiPath, fullSnapshotPath);

execFileSync(
  "pnpm",
  [
    "exec",
    "biome",
    "format",
    "--write",
    fullOpenApiPath,
    fullSnapshotPath,
    controlPlaneOpenApiPath,
  ],
  { stdio: "inherit" },
);
