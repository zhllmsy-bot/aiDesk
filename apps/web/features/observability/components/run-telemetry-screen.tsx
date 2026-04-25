"use client";

import Link from "next/link";

import { Button, CodeBlock, Panel, Stack, StatusBadge } from "@ai-desk/ui";

import {
  backlogViewModel,
  notificationViewModel,
  traceViewModel,
  workerHealthViewModel,
} from "@/features/runs/view-models/runtime-view-models";
import { useRunNotifications } from "../hooks/use-run-notifications";
import { useRunTrace } from "../hooks/use-run-trace";
import { useRuntimeBacklog } from "../hooks/use-runtime-backlog";
import { useRuntimeSla } from "../hooks/use-runtime-sla";
import { useWorkerHealth } from "../hooks/use-worker-health";

function formatTrendTimestamp(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatLatency(value: number | null | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "n/a";
  }
  if (value < 1) {
    return `${Math.round(value * 1000)} ms`;
  }
  return `${Math.round(value)} s`;
}

function formatRate(numerator: number, denominator: number) {
  if (denominator <= 0) {
    return "0%";
  }
  return `${Math.round((numerator / denominator) * 100)}%`;
}

export function RunTelemetryScreen({ runId }: { runId: string }) {
  const traceQuery = useRunTrace(runId);
  const notificationsQuery = useRunNotifications(runId);
  const workerQuery = useWorkerHealth();
  const backlogQuery = useRuntimeBacklog(runId);
  const traceProjectId =
    traceQuery.data?.spans.find((span) => span.correlation.projectId)?.correlation.projectId ??
    undefined;
  const runtimeSlaQuery = useRuntimeSla({
    projectId: traceProjectId,
    bucketMinutes: 60,
    windowHours: 24 * 7,
    enabled: Boolean(traceQuery.data),
  });

  if (traceQuery.isLoading || !traceQuery.data || !backlogQuery.data) {
    return <div className="surface-note">Loading telemetry view...</div>;
  }

  const trace = traceViewModel(traceQuery.data);
  const notifications = (notificationsQuery.data ?? []).map(notificationViewModel);
  const workers = (workerQuery.data ?? []).map(workerHealthViewModel);
  const backlog = backlogViewModel(backlogQuery.data);
  const runtimeSla = runtimeSlaQuery.data;
  const runtimeSlaTrend = (runtimeSla?.trend.points ?? []).slice(-6).reverse();
  const notificationFailureRate = formatRate(
    runtimeSla?.notifications.failed ?? 0,
    runtimeSla?.notifications.total ?? 0,
  );
  const notificationChannels = runtimeSla?.notifications.channels.length
    ? runtimeSla.notifications.channels.join(", ")
    : "none";
  const scopeProjectId = runtimeSla?.scope.project_id ?? traceProjectId ?? "all";
  const scopeIterationId = runtimeSla?.scope.iteration_id ?? "all";
  const scopeWindowHours = runtimeSla?.window_hours ?? 24 * 7;
  const scopeBucketMinutes = runtimeSla?.trend.bucket_minutes ?? 60;

  return (
    <div className="page-stack">
      <div className="inline-actions">
        <Link href={`/runs/${runId}/timeline`}>
          <Button tone="ghost">Back to timeline</Button>
        </Link>
      </div>

      <Panel eyebrow="Trace Correlation" title={`Trace ${trace.traceId}`}>
        <div className="hero-grid">
          <div className="hero-copy">
            <div className="inline-actions">
              <StatusBadge label={trace.workflowStatus} tone="warning" />
              <StatusBadge label={`root ${trace.rootSpanId}`} tone="info" />
            </div>
            <p className="ui-copy">
              Telemetry is normalized into spans and correlated with workflow, task, and attempt
              identifiers so product and engineering can debug the same narrative.
            </p>
            <div className="meta-row">
              <span>Started: {trace.startedAtLabel}</span>
              <span>Updated: {trace.updatedAtLabel}</span>
            </div>
          </div>
          <div className="hero-metrics">
            <div className="metric-card">
              <span className="ui-eyebrow">Queue depth</span>
              <strong>{backlog.queueDepth}</strong>
              <p className="ui-copy">Runtime backlog waiting behind worker capacity.</p>
            </div>
            <div className="metric-card">
              <span className="ui-eyebrow">Event lag</span>
              <strong>{backlog.eventLagSeconds}s</strong>
              <p className="ui-copy">Projection delay between emit and dashboard availability.</p>
            </div>
          </div>
        </div>
      </Panel>

      <Panel eyebrow="Runtime SLA" title="Recovery and delivery window">
        <div className="hero-grid">
          <div className="hero-copy">
            <p className="ui-copy">
              Snapshot rolls up retry recovery, approval resolution, failure recovery, and
              notification delivery into a shared product SLO view.
            </p>
            <div className="meta-row">
              <span>Project: {scopeProjectId}</span>
              <span>Iteration: {scopeIterationId}</span>
              <span>Window: {scopeWindowHours}h</span>
              <span>Bucket: {scopeBucketMinutes}m</span>
            </div>
          </div>

          <div className="hero-metrics">
            <div className="metric-card">
              <span className="ui-eyebrow">Approval p95</span>
              <strong>{formatLatency(runtimeSla?.approval_resolution.p95_seconds)}</strong>
              <p className="ui-copy">{runtimeSla?.approval_resolution.count ?? 0} approvals.</p>
            </div>
            <div className="metric-card">
              <span className="ui-eyebrow">Retry recovered</span>
              <strong>{runtimeSla?.retry_recovery.count ?? 0}</strong>
              <p className="ui-copy">
                avg {formatLatency(runtimeSla?.retry_recovery.avg_seconds)} to recover.
              </p>
            </div>
            <div className="metric-card">
              <span className="ui-eyebrow">Failure recovered</span>
              <strong>{runtimeSla?.failure_recovery.count ?? 0}</strong>
              <p className="ui-copy">
                p95 {formatLatency(runtimeSla?.failure_recovery.p95_seconds)} across incidents.
              </p>
            </div>
            <div className="metric-card">
              <span className="ui-eyebrow">Notification failure rate</span>
              <strong>{notificationFailureRate}</strong>
              <p className="ui-copy">channels: {notificationChannels}</p>
            </div>
          </div>
        </div>

        <Stack gap="var(--space-3)">
          {runtimeSlaTrend.length ? (
            runtimeSlaTrend.map((point) => (
              <div key={point.bucket_start} className="list-card">
                <div className="list-card-header">
                  <strong>{formatTrendTimestamp(point.bucket_start)}</strong>
                  <StatusBadge
                    label={`notify fail ${point.notifications_failed}/${point.notifications_total}`}
                    tone={point.notifications_failed > 0 ? "danger" : "success"}
                  />
                </div>
                <div className="meta-row">
                  <span>events {point.event_count}</span>
                  <span>retrying {point.workflow_retrying_count}</span>
                  <span>approval resolved {point.approval_resolved_count}</span>
                  <span>retry recovered {point.retry_recovered_count}</span>
                  <span>failure recovered {point.failure_recovered_count}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="surface-note">
              No SLA trend points are available yet for this scope.
            </div>
          )}
        </Stack>
      </Panel>

      <div className="detail-grid">
        <Panel eyebrow="Span Tree" title="Correlated spans">
          <Stack gap="var(--space-3)">
            {trace.spans.map((span) => (
              <article
                key={span.spanId}
                className="list-card"
                id={`trace-${trace.traceId}`}
                style={{ marginLeft: `${span.depth * 1.25}rem` }}
              >
                <div className="list-card-header">
                  <div>
                    <div className="ui-eyebrow">{span.kind}</div>
                    <strong>{span.name}</strong>
                  </div>
                  <StatusBadge label={span.status} tone={span.statusTone} />
                </div>
                <p className="ui-copy">{span.summary ?? "No span summary."}</p>
                <div className="meta-row">
                  <span>{span.startedAtLabel}</span>
                  <span>{span.endedAtLabel}</span>
                  <span>{span.durationMs} ms</span>
                  {span.correlation.taskId ? <span>task: {span.correlation.taskId}</span> : null}
                </div>
                <CodeBlock code={JSON.stringify(span.attributes, null, 2)} language="json" />
              </article>
            ))}
          </Stack>
        </Panel>

        <div className="detail-sidebar">
          <Panel eyebrow="Runtime Health" title="Workers and backlog">
            <Stack gap="var(--space-3)">
              <div className="surface-note">
                Last heartbeat {backlog.lastHeartbeatLabel}, waiting signals{" "}
                {backlog.waitingSignals}, lag tone {backlog.lagTone}.
              </div>
              {workers.map((worker) => (
                <div key={worker.workerId} className="list-card">
                  <div className="list-card-header">
                    <strong>{worker.workerId}</strong>
                    <StatusBadge label={worker.status} tone={worker.statusTone} />
                  </div>
                  <p className="ui-copy">{worker.detail}</p>
                  <div className="meta-row">
                    <span>{worker.taskQueue}</span>
                    <span>{worker.lastSeenAtLabel}</span>
                    <span>{worker.activeWorkflowNames.join(", ")}</span>
                  </div>
                </div>
              ))}
            </Stack>
          </Panel>

          <Panel eyebrow="Notifications" title="Delivery records">
            <Stack gap="var(--space-3)">
              {notifications.map((notification) => (
                <div key={notification.notificationId} className="list-card">
                  <div className="list-card-header">
                    <strong>{notification.channel}</strong>
                    <StatusBadge label={notification.status} tone={notification.statusTone} />
                  </div>
                  <p className="ui-copy">{notification.summary}</p>
                  <div className="meta-row">
                    <span>{notification.target}</span>
                    <span>{notification.deliveredAtLabel}</span>
                  </div>
                </div>
              ))}
            </Stack>
          </Panel>
        </div>
      </div>
    </div>
  );
}
