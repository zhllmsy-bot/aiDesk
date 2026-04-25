import type { TaskGraphReadModel } from "@ai-desk/contracts-runtime";

import { getTaskGraphFixture } from "../fixtures/runtime-data";
import { fetchTaskGraphLive } from "./runtime-live";

export async function getTaskGraph(runId: string): Promise<TaskGraphReadModel> {
  try {
    return await fetchTaskGraphLive(runId);
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 120));
  }

  const graph = getTaskGraphFixture(runId);
  if (!graph) {
    throw new Error(`Task graph ${runId} not found`);
  }

  return graph;
}
