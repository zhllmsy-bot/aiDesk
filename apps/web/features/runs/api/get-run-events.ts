import type { RunEvent } from "@ai-desk/contracts-runtime";

import { listRunEvents } from "@/lib/demo-data/runtime-data";
import { fetchRunEventsLive } from "./runtime-live";

export async function getRunEvents(runId: string): Promise<RunEvent[]> {
  try {
    return await fetchRunEventsLive(runId);
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  return listRunEvents(runId);
}
