import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const failures = [];

const requiredFiles = [
  "CONTRIBUTING.md",
  "SECURITY.md",
  "docs/roadmap.md",
  ".github/ISSUE_TEMPLATE/bug_report.yml",
  ".github/ISSUE_TEMPLATE/feature_request.yml",
  ".github/ISSUE_TEMPLATE/config.yml",
];

for (const file of requiredFiles) {
  if (!existsSync(join(root, file))) {
    failures.push(`${file} is required for public collaboration readiness.`);
  }
}

const read = (file) => readFileSync(join(root, file), "utf8");

const readme = read("README.md");
for (const needle of ["CONTRIBUTING.md", "SECURITY.md", "docs/roadmap.md"]) {
  if (!readme.includes(needle)) {
    failures.push(`README.md must link ${needle}.`);
  }
}

if (/infra\/deploy/.test(readme)) {
  failures.push("README.md still references the removed infra/deploy path.");
}

const contributing = read("CONTRIBUTING.md");
for (const command of ["pnpm lint", "pnpm typecheck", "pnpm test", "pnpm build"]) {
  if (!contributing.includes(command)) {
    failures.push(`CONTRIBUTING.md must mention ${command}.`);
  }
}

const roadmap = read("docs/roadmap.md");
for (const milestone of [
  "v0.1 Self-Hosted Beta",
  "v0.2 Multi-Tenant Alpha",
  "v0.3 Managed/SaaS Readiness",
]) {
  if (!roadmap.includes(milestone)) {
    failures.push(`docs/roadmap.md must include ${milestone}.`);
  }
}

if (failures.length) {
  console.error(failures.map((failure) => `- ${failure}`).join("\n"));
  process.exit(1);
}

console.info("Ecosystem readiness OK.");
