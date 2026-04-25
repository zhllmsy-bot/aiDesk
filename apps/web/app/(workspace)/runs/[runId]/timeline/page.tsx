import { RunOverviewScreen } from "@/features/runs/components/run-overview-screen";

export default async function RunTimelinePage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <RunOverviewScreen runId={runId} />;
}
