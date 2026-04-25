import type { TaskAttempt } from "@ai-desk/contracts-runtime";

import { getTaskAttemptsFixture } from "@/lib/demo-data/runtime-data";
import { fetchTaskAttemptsLive } from "./runtime-live";

export async function getTaskAttempts(runId: string, taskId: string): Promise<TaskAttempt[]> {
  try {
    return await fetchTaskAttemptsLive(runId, taskId);
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 90));
  }

  return getTaskAttemptsFixture(runId, taskId);
}
