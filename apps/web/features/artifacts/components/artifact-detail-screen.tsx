import Link from "next/link";

import { Button, Panel, StatusBadge } from "@ai-desk/ui";

import { getArtifactFixture } from "@/lib/demo-data/artifact-data";

export function ArtifactDetailScreen({ artifactId }: { artifactId: string }) {
  const artifact = getArtifactFixture(artifactId);

  if (!artifact) {
    return <div className="empty-state">Artifact {artifactId} is unavailable.</div>;
  }

  return (
    <div className="page-stack">
      <Panel
        eyebrow="Artifact"
        title={artifact.name}
        actions={<StatusBadge label={artifact.type} tone="info" />}
      >
        <div className="detail-grid">
          <div className="detail-main">
            <p className="run-lead">{artifact.summary}</p>
            <div className="surface-note">{artifact.id}</div>
          </div>
          <div className="detail-sidebar">
            <div className="kv-grid">
              <div className="kv-row">
                <span>Run</span>
                <strong>{artifact.runId}</strong>
              </div>
              <div className="kv-row">
                <span>Task</span>
                <strong>{artifact.taskId}</strong>
              </div>
              <div className="kv-row">
                <span>Attempt</span>
                <strong>{artifact.attemptId}</strong>
              </div>
            </div>
            <Link href={`/runs/${artifact.runId}/timeline`}>
              <Button>Open runtime proof</Button>
            </Link>
          </div>
        </div>
      </Panel>
    </div>
  );
}
