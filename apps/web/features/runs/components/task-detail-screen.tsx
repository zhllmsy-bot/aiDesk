import Link from "next/link";

import { Button, Panel, StatusBadge } from "@ai-desk/ui";

import { taskAttemptViewModel, taskDetailViewModel } from "@/lib/view-models/runtime-view-models";
import { getTaskAttempts } from "../api/get-task-attempts";
import { getTaskDetail } from "../api/get-task-detail";

export async function TaskDetailScreen({ runId, taskId }: { runId: string; taskId: string }) {
  const [task, attempts] = await Promise.all([
    getTaskDetail(runId, taskId),
    getTaskAttempts(runId, taskId),
  ]);
  const detail = taskDetailViewModel(task);
  const attemptItems = attempts.map((attempt) =>
    taskAttemptViewModel(attempt, task.projectId, runId),
  );

  return (
    <div className="page-stack">
      <div className="inline-actions">
        <Link href={`/runs/${runId}/timeline`}>
          <Button tone="ghost">Back to timeline</Button>
        </Link>
        <Link href={detail.projectRunHref}>
          <Button tone="secondary">Project run</Button>
        </Link>
      </div>

      <Panel eyebrow="Task detail" title={detail.title}>
        <div className="hero-grid">
          <div className="hero-copy">
            <div className="inline-actions">
              <StatusBadge label={detail.statusLabel} tone={detail.statusTone} />
              <StatusBadge label={detail.executor} tone="info" />
              <StatusBadge label={detail.verificationStatus} tone={detail.verificationTone} />
            </div>
            <p className="ui-copy">{detail.description}</p>
            <div className="meta-row">
              <span>Retries: {detail.retryCount}</span>
              <span>Failure: {detail.failureCategoryLabel}</span>
              <span>Blocked: {detail.blockedReason ?? "none"}</span>
            </div>
          </div>
          <div className="hero-metrics">
            <div className="metric-card">
              <span className="ui-eyebrow">Verification</span>
              <strong>{detail.verificationStatus}</strong>
              <p className="ui-copy">{detail.verificationSummary}</p>
            </div>
            <div className="metric-card">
              <span className="ui-eyebrow">Artifacts</span>
              <strong>{detail.linkedArtifactIds.length}</strong>
              <p className="ui-copy">Linked evidence from executor output.</p>
            </div>
          </div>
        </div>
      </Panel>

      <Panel eyebrow="Attempts" title="Attempt history">
        <div className="detail-list">
          {attemptItems.map((attempt) => (
            <article key={attempt.attemptId} className="list-card">
              <div className="list-card-header">
                <strong>{attempt.attemptId}</strong>
                <StatusBadge label={attempt.statusLabel} tone={attempt.statusTone} />
              </div>
              <div className="meta-row">
                <span>{attempt.startedAtLabel}</span>
                <span>{attempt.endedAtLabel}</span>
                <span>{attempt.taskId}</span>
              </div>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
