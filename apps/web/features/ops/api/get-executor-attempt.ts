import type { ExecutorAttempt } from "@ai-desk/contracts-execution";

import { getApiErrorMessage, getApiHeaders, webApiClient } from "@/lib/api-client";
import { getExecutorAttemptFixture } from "@/lib/demo-data/ops-data";

export async function getExecutorAttempt(attemptId: string): Promise<ExecutorAttempt> {
  try {
    const { data, error, response } = await webApiClient.GET("/review/attempts/{attempt_id}", {
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
    return data as ExecutorAttempt;
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 120));
    const attempt = getExecutorAttemptFixture(attemptId);
    if (!attempt) {
      throw new Error(`Executor attempt ${attemptId} not found`);
    }
    return attempt;
  }
}
