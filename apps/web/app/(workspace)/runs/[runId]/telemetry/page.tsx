import { RunTelemetryShell } from "@/features/observability/components/run-telemetry-shell";

export default async function RunTelemetryPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <RunTelemetryShell runId={runId} />;
}
