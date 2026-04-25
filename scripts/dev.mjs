import { spawn } from "node:child_process";

const child = spawn(
  "pnpm",
  [
    "exec",
    "concurrently",
    "-k",
    "-n",
    "api,web",
    "pnpm --filter @ai-desk/api dev",
    "pnpm --filter @ai-desk/web dev",
  ],
  {
    shell: true,
    stdio: "inherit",
  },
);

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
