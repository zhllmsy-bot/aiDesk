import { spawn, spawnSync } from "node:child_process";

if (process.env.AI_DESK_SKIP_INFRA !== "1") {
  for (const [command, args] of [
    ["pnpm", ["infra:up"]],
    ["pnpm", ["db:migrate"]],
  ]) {
    const result = spawnSync(command, args, {
      shell: true,
      stdio: "inherit",
    });

    if (result.status !== 0) {
      process.exit(result.status ?? 1);
    }
  }
}

const child = spawn(
  "pnpm",
  [
    "exec",
    "concurrently",
    "-k",
    "-n",
    "api,web,worker",
    "pnpm --filter @ai-desk/api dev",
    "pnpm --filter @ai-desk/web dev",
    "pnpm --filter @ai-desk/worker dev",
  ],
  {
    shell: true,
    stdio: "inherit",
  },
);

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
