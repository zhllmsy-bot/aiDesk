import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
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
  "Avatar",
  "Badge",
  "Breadcrumb",
  "Button",
  "Card",
  "DescriptionList",
  "Input",
  "PageLayout",
  "SearchInput",
  "Select",
  "SegmentedControl",
  "Sidebar",
  "StatCard",
  "Dialog",
  "Sheet",
  "Toast",
  "Table",
  "Tabs",
  "Tooltip",
];
const requiredWebDependencies = [
  "@ai-desk/ui",
  "@hookform/resolvers",
  "@radix-ui/react-dialog",
  "@radix-ui/react-select",
  "@radix-ui/react-tabs",
  "@radix-ui/react-toast",
  "@radix-ui/react-tooltip",
  "class-variance-authority",
  "framer-motion",
  "lucide-react",
  "next-intl",
  "react-hook-form",
  "tailwind-variants",
];
const requiredWebDevDependencies = ["@tailwindcss/postcss", "tailwindcss"];
const requiredProductRouteFiles = [
  "apps/web/app/(workspace)/projects/page.tsx",
  "apps/web/app/(workspace)/projects/[projectId]/page.tsx",
  "apps/web/app/(workspace)/projects/[projectId]/audit/page.tsx",
  "apps/web/app/(workspace)/review/page.tsx",
  "apps/web/app/(workspace)/artifacts/page.tsx",
  "apps/web/app/(workspace)/artifacts/[artifactId]/page.tsx",
  "apps/web/app/(workspace)/ops/attempts/[attemptId]/page.tsx",
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

function isCssFile(path) {
  return /\.css$/.test(path);
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
  if (/\bas\s+any\b/.test(source)) {
    failures.push(`${path} uses as any; fix the type boundary instead.`);
  }
  if (/\/\/\s*@ts-(ignore|expect-error)|\/\*\s*@ts-(ignore|expect-error)/.test(source)) {
    failures.push(`${path} suppresses TypeScript diagnostics.`);
  }
  if (/[\u3400-\u9fff]/.test(source)) {
    failures.push(`${path} contains hard-coded CJK copy; route UI copy through i18n.`);
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
  if (path.startsWith("apps/web/") && /@radix-ui\/react-/.test(source)) {
    failures.push(`${path} imports Radix directly; use @ai-desk/ui primitives.`);
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

for (const file of walk(join(root, "apps/web")).filter(isCssFile)) {
  const source = readFileSync(file, "utf8");
  const path = rel(file);
  if (/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(source)) {
    failures.push(`${path} contains hard-coded colors; consume tokens from packages/ui.`);
  }
}

const webPackagePath = join(root, "apps/web/package.json");
const webPackage = JSON.parse(readFileSync(webPackagePath, "utf8"));
for (const dependency of requiredWebDependencies) {
  if (!webPackage.dependencies?.[dependency]) {
    failures.push(`apps/web/package.json must declare dependency ${dependency}.`);
  }
}
for (const dependency of requiredWebDevDependencies) {
  if (!webPackage.devDependencies?.[dependency]) {
    failures.push(`apps/web/package.json must declare devDependency ${dependency}.`);
  }
}

for (const file of requiredProductRouteFiles) {
  if (!existsSync(join(root, file))) {
    failures.push(`${file} is required for first-run project and audit onboarding.`);
  }
}

if (!existsSync(join(root, "apps/worker/package.json"))) {
  failures.push("apps/worker/package.json is required so runtime worker is a workspace package.");
}

const postcssConfigPath = join(root, "apps/web/postcss.config.mjs");
if (!existsSync(postcssConfigPath)) {
  failures.push("apps/web/postcss.config.mjs is required for Tailwind v4.");
}

const webGlobalsPath = join(root, "apps/web/app/globals.css");
const webGlobals = readFileSync(webGlobalsPath, "utf8");
if (!webGlobals.includes('@import "tailwindcss";')) {
  failures.push('apps/web/app/globals.css must import "tailwindcss".');
}
if (!webGlobals.includes('@import "@ai-desk/ui/styles.css";')) {
  failures.push('apps/web/app/globals.css must import "@ai-desk/ui/styles.css".');
}
if (/^\s*\.[_a-zA-Z-][\w-]*\s*[{,]/m.test(webGlobals)) {
  failures.push(
    "apps/web/app/globals.css must not define business classes; move them to @ai-desk/ui or feature CSS.",
  );
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
