import type { ApprovalSummary } from "@ai-desk/contracts-execution";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function approvalStatusLabel(status: ApprovalSummary["status"]) {
  return status.replaceAll("_", " ");
}

export function approvalListItemViewModel(approval: ApprovalSummary) {
  const statusTone: BadgeTone =
    approval.status === "approved"
      ? "success"
      : approval.status === "rejected" || approval.status === "expired"
        ? "danger"
        : "warning";
  const riskTone: BadgeTone =
    approval.riskLevel === "critical" || approval.riskLevel === "high"
      ? "danger"
      : approval.riskLevel === "medium"
        ? "warning"
        : "info";

  return {
    ...approval,
    statusTone,
    riskTone,
    requestedAtLabel: formatTimestamp(approval.requestedAt),
    linkHref: `/review/${approval.id}`,
  };
}
