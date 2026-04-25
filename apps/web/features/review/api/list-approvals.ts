import type { ApprovalSummary } from "@ai-desk/contracts-execution";

import { getApiErrorMessage, getApiHeaders, webApiClient } from "@/lib/api-client";
import { listApprovalFixtures } from "../fixtures/review-data";

export async function listApprovals(): Promise<ApprovalSummary[]> {
  try {
    const { data, error, response } = await webApiClient.GET("/review/approvals", {
      headers: await getApiHeaders(),
    });
    if (!data) {
      throw new Error(getApiErrorMessage(error, response.status));
    }
    return data.items as ApprovalSummary[];
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 120));
    return listApprovalFixtures();
  }
}
