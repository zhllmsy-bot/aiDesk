import type { EvidenceRef } from "@ai-desk/contracts-execution";

import { getApiErrorMessage, getApiHeaders, webApiClient } from "@/lib/api-client";
import { getEvidenceFixture } from "@/lib/demo-data/ops-data";

export async function getEvidence(attemptId: string): Promise<EvidenceRef[]> {
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
    return data.evidenceRefs as EvidenceRef[];
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 100));
    return getEvidenceFixture(attemptId);
  }
}
