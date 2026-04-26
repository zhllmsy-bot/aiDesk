import { readFileSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const root = process.cwd();
const barrelPath = join(root, "packages/ui/src/index.tsx");
const manifestPath = join(root, "packages/ui/manifest.json");

function buildManifest() {
  const source = readFileSync(barrelPath, "utf8");
  const exportPattern = /^export\s*\{([^}]+)\}\s*from\s*"(.+?)";$/gm;
  const components = [];

  for (const match of source.matchAll(exportPattern)) {
    const [, exportList, modulePath] = match;
    const relativeSource = modulePath.replace(/^\.\//, "src/").replace(/$/, ".tsx");

    for (const entry of exportList.split(",")) {
      const normalized = entry.trim();
      if (!normalized || normalized.startsWith("type ")) {
        continue;
      }
      const [name] = normalized.split(/\s+as\s+/);
      components.push({
        name: name.trim(),
        source: relativeSource,
      });
    }
  }

  return {
    components: components.sort((left, right) => left.name.localeCompare(right.name)),
    source: relative(root, barrelPath),
  };
}

const manifest = buildManifest();
writeFileSync(`${manifestPath}`, `${JSON.stringify(manifest, null, 2)}\n`);
