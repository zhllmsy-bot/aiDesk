"use client";

import dynamic from "next/dynamic";

const RunTelemetryScreen = dynamic(
  () => import("./run-telemetry-screen").then((module) => module.RunTelemetryScreen),
  {
    loading: () => <div className="surface-note">Loading telemetry view...</div>,
    ssr: false,
  },
);

export function RunTelemetryShell({ runId }: { runId: string }) {
  return <RunTelemetryScreen runId={runId} />;
}
