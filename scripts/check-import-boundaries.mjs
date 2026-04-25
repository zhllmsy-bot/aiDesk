import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const root = process.cwd();
const apiRoot = join(root, "apps/api/api");

const llmSdkImports = [
  "anthropic",
  "openai",
  "google-genai",
  "google_genai",
  "google.generativeai",
  "google.genai",
];

function walk(dir) {
  const entries = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const stat = statSync(path);
    if (stat.isDirectory()) {
      entries.push(...walk(path));
    } else {
      entries.push(path);
    }
  }
  return entries;
}

function isServiceFile(path) {
  return path.endsWith("/service.py") || path.endsWith("\\service.py");
}

function isAllowedLlmBoundary(path) {
  return path.includes("/api/integrations/llm/") || path.includes("\\api\\integrations\\llm\\");
}

function hasRestrictedImport(source, moduleName) {
  const escaped = moduleName.replaceAll(".", "\\.");
  const patterns = [
    new RegExp(`^\\s*import\\s+${escaped}(\\s|\\.|$)`, "m"),
    new RegExp(`^\\s*from\\s+${escaped}(\\s|\\.|$)`, "m"),
  ];
  return patterns.some((pattern) => pattern.test(source));
}

const failures = [];

for (const file of walk(apiRoot).filter((path) => path.endsWith(".py"))) {
  const source = readFileSync(file, "utf8");

  if (isServiceFile(file) && !isAllowedLlmBoundary(file)) {
    for (const moduleName of llmSdkImports) {
      if (hasRestrictedImport(source, moduleName)) {
        failures.push(
          `${relative(root, file)} imports ${moduleName}; route LLM access through api.integrations.llm instead.`,
        );
      }
    }
  }

  const path = relative(root, file);
  if (
    (path.startsWith("apps/api/api/domain/") || path.startsWith("apps/api/api/kernel/")) &&
    /from\s+api\.integrations\.|import\s+api\.integrations\./.test(source)
  ) {
    failures.push(`${path} imports concrete integrations; depend on contracts or protocols.`);
  }
  if (
    path.startsWith("apps/api/api/integrations/") &&
    /from\s+api\.[\w.]+\.router\b|import\s+api\.[\w.]+\.router\b/.test(source)
  ) {
    failures.push(`${path} imports a router; integrations must stay below application IO.`);
  }
}

if (failures.length) {
  console.error("Import boundary violations:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

process.stdout.write("Import boundaries OK.\n");
