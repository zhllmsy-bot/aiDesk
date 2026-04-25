import Link from "next/link";

import { Button, Panel } from "@ai-desk/ui";

import { getRunRecord } from "@/lib/demo-data/runtime-data";

export function ProjectRunDetailScreen({
  projectId,
  runId,
}: {
  projectId: string;
  runId: string;
}) {
  const run = getRunRecord(runId);

  if (!run || run.projectId !== projectId) {
    return <div className="empty-state">Project-scoped run {runId} is unavailable.</div>;
  }

  return (
    <div className="page-stack">
      <Panel eyebrow="Project run" title={`${run.projectName} / ${run.id}`}>
        <div className="hero-grid">
          <div className="hero-copy">
            <p className="ui-copy">
              A project-scoped view of this autonomous run. Open the command surface for live event
              history, active task state, and telemetry.
            </p>
            <div className="inline-actions">
              <Link href={`/runs/${runId}/timeline`}>
                <Button>Open command</Button>
              </Link>
              <Link href={`/runs/${runId}/tasks/${run.currentTaskId}`}>
                <Button tone="secondary">Open current task</Button>
              </Link>
              <Link href={`/runs/${runId}/telemetry`}>
                <Button tone="ghost">Open telemetry</Button>
              </Link>
            </div>
          </div>
          <div className="hero-metrics">
            <div className="metric-card">
              <span className="ui-eyebrow">Workflow status</span>
              <strong>{run.workflowStatus}</strong>
              <p className="ui-copy">{run.statusReason}</p>
            </div>
            <div className="metric-card">
              <span className="ui-eyebrow">Current task</span>
              <strong>{run.currentTaskId}</strong>
              <p className="ui-copy">{run.currentTaskTitle}</p>
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}
