import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const outputDir = join(root, "apps/api/api/generated_contracts");

mkdirSync(outputDir, { recursive: true });

execFileSync(
  "uv",
  [
    "run",
    "--project",
    "apps/api",
    "datamodel-codegen",
    "--input",
    "packages/contracts/api/openapi/full.openapi.json",
    "--input-file-type",
    "openapi",
    "--output",
    "apps/api/api/generated_contracts/openapi_models.py",
    "--output-model-type",
    "pydantic_v2.BaseModel",
    "--target-python-version",
    "3.12",
    "--disable-timestamp",
  ],
  { cwd: root, stdio: "inherit" },
);
