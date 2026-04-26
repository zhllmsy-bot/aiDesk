import { ApprovalCenterShell } from "@/features/review/components/approval-center-shell";
import { getApprovalCenterCopy } from "@/features/review/i18n";

export default async function ReviewPage() {
  return <ApprovalCenterShell copy={await getApprovalCenterCopy()} />;
}
