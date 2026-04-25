import Link from "next/link";

import { Button, Panel } from "@ai-desk/ui";

import { projectRoutes } from "../routes";

export function ProjectReviewEntryScreen({ projectId }: { projectId: string }) {
  return (
    <Panel eyebrow="Decision entry" title="Project approval queue">
      <p className="ui-copy">
        Project-scoped entry for approvals that can pause, resume, or redirect autonomous work.
      </p>
      <div className="inline-actions">
        <Link href="/review">
          <Button>Open approval center</Button>
        </Link>
        <Link href={projectRoutes.detail({ projectId })}>
          <Button tone="secondary">Back to project</Button>
        </Link>
      </div>
    </Panel>
  );
}
