import { execFileSync } from "node:child_process";

function gitConfig(key) {
  try {
    return execFileSync("git", ["config", "--get", key], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "";
  }
}

const name = gitConfig("user.name");
const email = gitConfig("user.email");
const failures = [];

if (!name || name === "Your Name") {
  failures.push("git user.name is still unset or placeholder.");
}

if (!email || email === "you@example.com") {
  failures.push("git user.email is still unset or placeholder.");
}

if (failures.length) {
  console.error(failures.map((failure) => `- ${failure}`).join("\n"));
  process.exit(1);
}

console.info(`Local git identity OK: ${name} <${email}>`);
