import type { ApprovalDetail, ApprovalSummary } from "@ai-desk/contracts-execution";

let approvals: ApprovalDetail[] = [
  {
    id: "aprv_patch_guard",
    schemaVersion: "2026-04-19.execution.v1",
    type: "write_execution",
    title: "Guarded workflow patch",
    reason: "Approval required for guarded workflow patch.",
    status: "pending",
    riskLevel: "high",
    requestedAt: "2026-04-19T00:43:05Z",
    requestedBy: { id: "runtime-worker", name: "Runtime Worker", role: "system" },
    correlation: {
      projectId: "proj_meridian",
      runId: "run_20260419_main",
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    relatedArtifacts: ["artifact_patch_001"],
  },
];

export function listApprovalFixtures(): ApprovalSummary[] {
  return approvals.map(({ expiresAt, relatedArtifacts, resolutionNote, ...approval }) => approval);
}

export function getApprovalFixture(approvalId: string) {
  return approvals.find((approval) => approval.id === approvalId) ?? null;
}

export function resolveApprovalFixture(input: {
  approvalId: string;
  status: "approved" | "rejected" | "expired";
  reason: string;
}) {
  const approvalIndex = approvals.findIndex((approval) => approval.id === input.approvalId);
  if (approvalIndex < 0) {
    return null;
  }
  const currentApproval = approvals[approvalIndex];
  if (!currentApproval) {
    return null;
  }
  const updated = {
    ...currentApproval,
    status: input.status,
    resolutionNote: input.reason,
  } satisfies ApprovalDetail;
  approvals = approvals.map((approval, index) => (index === approvalIndex ? updated : approval));
  return updated;
}
