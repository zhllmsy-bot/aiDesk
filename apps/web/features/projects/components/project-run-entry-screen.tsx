import Link from "next/link";

import { Button, Panel } from "@ai-desk/ui";

import { projectRoutes } from "../routes";
import { getRunContextLabel } from "../server/project-store";

export function ProjectRunEntryScreen({
  projectId,
  runId,
}: {
  projectId: string;
  runId: string;
}) {
  return (
    <Panel eyebrow="Run entry" title={runId}>
      <p className="ui-copy">
        Project-scoped entry for the run. Use the command surface for live history, subagent
        checklist, telemetry, and task evidence.
      </p>
      <div className="surface-note">{getRunContextLabel(runId)}</div>
      <div className="inline-actions">
        <Link href={projectRoutes.detail({ projectId })}>
          <Button tone="secondary">Back to project</Button>
        </Link>
        <Link href="/review">
          <Button>Open review workspace</Button>
        </Link>
      </div>
    </Panel>
  );
}
