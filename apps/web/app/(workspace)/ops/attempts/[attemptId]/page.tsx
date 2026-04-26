import { AttemptDetailScreen } from "@/features/ops/components/attempt-detail-screen";

export default async function AttemptDetailPage({
  params,
}: {
  params: Promise<{ attemptId: string }>;
}) {
  const { attemptId } = await params;
  return <AttemptDetailScreen attemptId={attemptId} />;
}
