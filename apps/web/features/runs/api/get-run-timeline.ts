import type { TimelineReadModel } from "@ai-desk/contracts-runtime";

import { getTimelineFixture } from "../fixtures/runtime-data";
import { fetchTimelineLive } from "./runtime-live";

export async function getRunTimeline(runId: string): Promise<TimelineReadModel> {
  try {
    return await fetchTimelineLive(runId);
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 110));
  }

  const timeline = getTimelineFixture(runId);
  if (!timeline) {
    throw new Error(`Run timeline ${runId} not found`);
  }

  return timeline;
}
