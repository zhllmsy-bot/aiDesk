import Link from "next/link";

import { Button, Panel, StatusBadge } from "@ai-desk/ui";

import { listArtifactFixtures } from "@/lib/demo-data/artifact-data";

export function ArtifactIndexScreen() {
  const artifacts = listArtifactFixtures();

  return (
    <div className="page-stack">
      <Panel
        eyebrow="Evidence"
        title="Artifact ledger"
        actions={<StatusBadge label={`${artifacts.length} linked`} tone="neutral" />}
      >
        <div className="list-grid">
          {artifacts.map((artifact) => (
            <article key={artifact.id} className="list-card">
              <div className="list-card-header">
                <div>
                  <div className="ui-eyebrow">{artifact.type}</div>
                  <h3 className="list-card-title">{artifact.name}</h3>
                </div>
                <StatusBadge label={artifact.runId} tone="info" />
              </div>
              <p className="ui-copy">{artifact.summary}</p>
              <div className="meta-row">
                <span>Task: {artifact.taskId}</span>
                <span>Attempt: {artifact.attemptId}</span>
                <span>Created: {artifact.createdAt}</span>
              </div>
              <Link href={artifact.href}>
                <Button>Open artifact</Button>
              </Link>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
