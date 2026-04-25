import type { ApprovalDetail } from "@ai-desk/contracts-execution";

import { getApiErrorMessage, getApiHeaders, webApiClient } from "@/lib/api-client";
import { getApprovalFixture } from "@/lib/demo-data/review-data";

export async function getApproval(approvalId: string): Promise<ApprovalDetail> {
  try {
    const { data, error, response } = await webApiClient.GET("/review/approvals/{approval_id}", {
      params: {
        path: {
          approval_id: approvalId,
        },
      },
      headers: await getApiHeaders(),
    });
    if (!data) {
      throw new Error(getApiErrorMessage(error, response.status));
    }
    return data as ApprovalDetail;
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 80));
    const approval = getApprovalFixture(approvalId);
    if (!approval) {
      throw new Error(`Approval ${approvalId} not found`);
    }
    return approval;
  }
}
