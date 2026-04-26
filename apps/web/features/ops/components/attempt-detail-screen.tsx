import Link from "next/link";

import { Button, Panel, StatusBadge } from "@ai-desk/ui";

import { getExecutorAttemptFixture } from "@/lib/demo-data/ops-data";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

function verdictTone(verdict: string): BadgeTone {
  if (verdict === "passed") {
    return "success";
  }
  if (verdict === "failed") {
    return "danger";
  }
  return "warning";
}

export function AttemptDetailScreen({ attemptId }: { attemptId: string }) {
  const attempt = getExecutorAttemptFixture(attemptId);

  if (!attempt) {
    return <div className="empty-state">Attempt {attemptId} is unavailable.</div>;
  }
  const evidenceRefs = attempt.evidenceRefs ?? [];
  const memoryHits = attempt.memoryHits ?? [];

  return (
    <div className="page-stack">
      <Panel
        eyebrow="Executor attempt"
        title={attempt.executor}
        actions={
          <StatusBadge
            label={attempt.verification.verdict}
            tone={verdictTone(attempt.verification.verdict)}
          />
        }
      >
        <div className="run-command-grid">
          <div className="run-command-main">
            <p className="run-lead">{attempt.summary}</p>
            <div className="signal-strip">
              <div className="signal-cell">
                <span>Run</span>
                <code>{attempt.correlation.runId}</code>
              </div>
              <div className="signal-cell">
                <span>Task</span>
                <code>{attempt.correlation.taskId}</code>
              </div>
              <div className="signal-cell">
                <span>Security</span>
                <strong>{attempt.security.approvalRequired ? "approval required" : "clear"}</strong>
              </div>
            </div>
          </div>
          <div className="run-command-todos">
            <div className="ui-eyebrow">Evidence</div>
            {evidenceRefs.map((evidence) => (
              <Link key={evidence.id} href={evidence.href}>
                <Button tone="secondary">{evidence.label}</Button>
              </Link>
            ))}
            <Link href={`/runs/${attempt.correlation.runId}/tasks/${attempt.correlation.taskId}`}>
              <Button>Open task</Button>
            </Link>
          </div>
        </div>
      </Panel>

      <Panel eyebrow="Memory" title="Recovered context">
        <div className="list-grid">
          {memoryHits.map((hit) => (
            <div key={hit.id} className="list-card">
              <div className="list-card-header">
                <strong>{hit.namespace}</strong>
                <StatusBadge label={`${hit.score}`} tone="info" />
              </div>
              <p className="ui-copy">{hit.summary}</p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
