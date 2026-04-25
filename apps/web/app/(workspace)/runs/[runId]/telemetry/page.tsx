import { RunTelemetryScreen } from "@/features/observability/components/run-telemetry-screen";

export default async function RunTelemetryPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <RunTelemetryScreen runId={runId} />;
}
