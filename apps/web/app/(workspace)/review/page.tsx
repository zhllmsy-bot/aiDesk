import { ApprovalCenterScreen } from "@/features/review/components/approval-center-screen";
import { getApprovalCenterCopy } from "@/features/review/i18n";

export default function ReviewPage() {
  return <ApprovalCenterScreen copy={getApprovalCenterCopy()} />;
}
