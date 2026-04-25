import { TaskDetailScreen } from "@/features/runs/components/task-detail-screen";

export default async function TaskDetailPage({
  params,
}: {
  params: Promise<{ runId: string; taskId: string }>;
}) {
  const { runId, taskId } = await params;
  return <TaskDetailScreen runId={runId} taskId={taskId} />;
}
