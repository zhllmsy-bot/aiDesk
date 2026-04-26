import { RunOverviewShell } from "@/features/runs/components/run-overview-shell";

export default async function RunTimelinePage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <RunOverviewShell runId={runId} />;
}
