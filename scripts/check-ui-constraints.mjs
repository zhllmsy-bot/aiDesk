import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const root = process.cwd();
const sourceRoots = ["apps/web", "packages/ui"].map((path) => join(root, path));
const failures = [];
const forbiddenImports = [
  "axios",
  "swr",
  "redux",
  "zustand",
  "jotai",
  "mobx",
  "styled-components",
  "@emotion/react",
  "@emotion/styled",
  "sass",
  "gsap",
  "animejs",
];
const requiredUiPrimitives = [
  "Button",
  "Input",
  "Select",
  "Dialog",
  "Sheet",
  "Toast",
  "Table",
  "Tabs",
  "Tooltip",
  "Badge",
];

function walk(dir) {
  const entries = [];
  for (const name of readdirSync(dir)) {
    if ([".next", "dist", "node_modules", "test-results", "playwright-report"].includes(name)) {
      continue;
    }
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

function rel(path) {
  return relative(root, path);
}

function lineCount(source) {
  return source.split(/\r?\n/).length;
}

function isSourceFile(path) {
  return /\.(ts|tsx|js|jsx)$/.test(path) && !path.endsWith("tsconfig.tsbuildinfo");
}

function featureNameFor(path) {
  const parts = rel(path).split(sep);
  const index = parts.indexOf("features");
  return index >= 0 ? parts[index + 1] : undefined;
}

function checkImportBoundaries(file, source) {
  const currentFeature = featureNameFor(file);
  const importPattern = /from\s+["']@\/features\/([^/"']+)\//g;
  for (const match of source.matchAll(importPattern)) {
    const targetFeature = match[1];
    if (currentFeature && targetFeature && currentFeature !== targetFeature) {
      failures.push(
        `${rel(file)} imports features/${targetFeature}; cross-feature imports must move through lib/ or packages/ui.`,
      );
    }
  }
}

for (const file of sourceRoots.flatMap(walk).filter(isSourceFile)) {
  const source = readFileSync(file, "utf8");
  const path = rel(file);

  if (path.includes("/fixtures/") || path.includes("\\fixtures\\")) {
    failures.push(
      `${path} is under fixtures; runtime fixtures are only allowed in tests/storybook.`,
    );
  }
  if (path.startsWith("apps/web/app/") && path.endsWith("/page.tsx") && lineCount(source) > 20) {
    failures.push(`${path} has ${lineCount(source)} lines; app/**/page.tsx must be <= 20.`);
  }
  if (
    path.startsWith("apps/web/app/api/") &&
    path.endsWith("/route.ts") &&
    lineCount(source) > 60
  ) {
    failures.push(`${path} has ${lineCount(source)} lines; app/api/**/route.ts must be <= 60.`);
  }
  if (/style=\{\{/.test(source)) {
    failures.push(`${path} uses inline style; move styling to tokens/classes.`);
  }
  if (/<img(\s|>)/.test(source)) {
    failures.push(`${path} uses <img>; use next/image or a design-system media primitive.`);
  }
  if (/console\.log\s*\(/.test(source)) {
    failures.push(`${path} uses console.log.`);
  }
  if (/\bfetch\s*\(/.test(source) && path !== "apps/web/lib/api-client.ts") {
    failures.push(`${path} calls fetch directly; use webFetch/apiFetch from lib/api-client.`);
  }
  if (/\b[a-z][a-z0-9-]*-\[[^\]]+\]/.test(source)) {
    failures.push(`${path} uses arbitrary Tailwind values; add a token or ADR-backed class.`);
  }
  if (/role=["']dialog["']/.test(source)) {
    failures.push(`${path} hand-rolls role="dialog"; use the Dialog primitive.`);
  }
  for (const moduleName of forbiddenImports) {
    const escaped = moduleName.replaceAll("/", "\\/");
    const pattern = new RegExp(`from\\s+["']${escaped}["']|import\\s+["']${escaped}["']`);
    if (pattern.test(source)) {
      failures.push(`${path} imports ${moduleName}; UI stack is closed unless an ADR adds it.`);
    }
  }
  checkImportBoundaries(file, source);
}

const uiIndexPath = join(root, "packages/ui/src/index.tsx");
const uiPrimitivesPath = join(root, "packages/ui/src/primitives.tsx");
const uiStoryPath = join(root, "packages/ui/src/primitives.stories.tsx");
const uiIndex = readFileSync(uiIndexPath, "utf8");
const uiPrimitives = readFileSync(uiPrimitivesPath, "utf8");
const uiStory = readFileSync(uiStoryPath, "utf8");
if (!uiIndex.includes("cva(")) {
  failures.push("packages/ui/src/index.tsx must use cva for primitive variants.");
}
for (const primitive of requiredUiPrimitives) {
  const primitivePattern = new RegExp(`\\b${primitive}\\b`);
  if (!primitivePattern.test(`${uiIndex}\n${uiPrimitives}`)) {
    failures.push(`packages/ui/src does not export ${primitive}.`);
  }
  if (!primitivePattern.test(uiStory)) {
    failures.push(`packages/ui/src/primitives.stories.tsx does not cover ${primitive}.`);
  }
}

for (const file of walk(join(root, "apps/web/components")).filter(isSourceFile)) {
  const path = rel(file);
  if (!path.startsWith("apps/web/components/layout/")) {
    failures.push(
      `${path} is a root component; move it to features/<x>/components or packages/ui.`,
    );
  }
}

if (failures.length) {
  console.error("UI constraint violations:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

process.stdout.write("UI constraints OK.\n");
