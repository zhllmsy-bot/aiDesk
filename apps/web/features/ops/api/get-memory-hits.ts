import type { MemoryHit } from "@ai-desk/contracts-execution";

import { getApiErrorMessage, getApiHeaders, webApiClient } from "@/lib/api-client";
import { getMemoryHitsFixture } from "../fixtures/ops-data";

export async function getMemoryHits(attemptId: string): Promise<MemoryHit[]> {
  try {
    const { data, error, response } = await webApiClient.GET("/review/evidence/{attempt_id}", {
      params: {
        path: {
          attempt_id: attemptId,
        },
      },
      headers: await getApiHeaders(),
    });
    if (!data) {
      throw new Error(getApiErrorMessage(error, response.status));
    }
    return data.memoryHits as MemoryHit[];
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 100));
    return getMemoryHitsFixture(attemptId);
  }
}
