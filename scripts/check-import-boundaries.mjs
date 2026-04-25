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
  if (!isServiceFile(file) || isAllowedLlmBoundary(file)) {
    continue;
  }
  const source = readFileSync(file, "utf8");
  for (const moduleName of llmSdkImports) {
    if (hasRestrictedImport(source, moduleName)) {
      failures.push(
        `${relative(root, file)} imports ${moduleName}; route LLM access through api.integrations.llm instead.`,
      );
    }
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
