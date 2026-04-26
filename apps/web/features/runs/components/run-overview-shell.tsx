"use client";

import dynamic from "next/dynamic";

const RunOverviewScreen = dynamic(
  () => import("./run-overview-screen").then((module) => module.RunOverviewScreen),
  {
    loading: () => <div className="surface-note">Loading runtime command view...</div>,
    ssr: false,
  },
);

export function RunOverviewShell({ runId }: { runId: string }) {
  return <RunOverviewScreen runId={runId} />;
}
