import { ApprovalDetailShell } from "@/features/review/components/approval-detail-shell";
import { getApprovalDetailCopy } from "@/features/review/i18n";

export default async function ApprovalDetailPage({
  params,
}: {
  params: Promise<{ approvalId: string }>;
}) {
  const { approvalId } = await params;
  return <ApprovalDetailShell approvalId={approvalId} copy={await getApprovalDetailCopy()} />;
}
