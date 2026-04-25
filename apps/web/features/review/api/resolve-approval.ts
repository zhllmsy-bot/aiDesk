import type { ApprovalDetail } from "@ai-desk/contracts-execution";

import { getApiErrorMessage, getApiHeaders, webApiClient } from "@/lib/api-client";
import { resolveApprovalFixture } from "../fixtures/review-data";

export async function resolveApproval(input: {
  approvalId: string;
  status: "approved" | "rejected" | "expired";
  reason: string;
}): Promise<ApprovalDetail> {
  try {
    const { data, error, response } = await webApiClient.POST(
      "/review/approvals/{approval_id}/resolve",
      {
        params: {
          path: {
            approval_id: input.approvalId,
          },
        },
        headers: await getApiHeaders({
          "Content-Type": "application/json",
        }),
        body: {
          decision: input.status,
          reason: input.reason,
          approvedWritePaths: [],
          metadata: {},
        },
      },
    );
    if (!data) {
      throw new Error(getApiErrorMessage(error, response.status));
    }
    return data as ApprovalDetail;
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 180));
    const approval = resolveApprovalFixture(input);
    if (!approval) {
      throw new Error(`Approval ${input.approvalId} not found`);
    }
    return approval;
  }
}
