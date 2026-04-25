import type { TaskDetailRecord } from "../types";

import { getTaskDetailFixture } from "../fixtures/runtime-data";
import { fetchTaskDetailLive } from "./runtime-live";

export async function getTaskDetail(runId: string, taskId: string): Promise<TaskDetailRecord> {
  try {
    return await fetchTaskDetailLive(runId, taskId);
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  const detail = getTaskDetailFixture(runId, taskId);
  if (!detail) {
    throw new Error(`Task detail ${taskId} not found in run ${runId}`);
  }

  return detail;
}
