import type {
  EventType,
  NotificationSummary,
  RunEvent,
  RuntimeBacklogSnapshot,
  TaskAttempt,
  TaskGraphNode,
  TraceCorrelation,
  TraceSpanRecord,
  WorkerHealthReadModel,
  WorkflowStatus,
} from "@ai-desk/contracts-runtime";

import type { TaskDetailRecord } from "@/features/runs/types";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const eventLabelMap: Record<EventType, string> = {
  "workflow.started": "Workflow Started",
  "workflow.completed": "Workflow Completed",
  "workflow.failed": "Workflow Failed",
  "workflow.retrying": "Workflow Retrying",
  "workflow.waiting_approval": "Workflow Waiting Approval",
  "task.claimed": "Task Claimed",
  "task.running": "Task Running",
  "task.verifying": "Task Verifying",
  "task.completed": "Task Completed",
  "task.failed": "Task Failed",
  "task.heartbeat": "Task Heartbeat",
  "task.reclaimed": "Task Reclaimed",
  "task.graph.updated": "Task Graph Updated",
  "task.todo.updated": "Task Todo Updated",
  "approval.requested": "Approval Requested",
  "approval.resolved": "Approval Resolved",
  "notification.sent": "Notification Sent",
  "artifact.linked": "Artifact Linked",
  "memory.recalled": "Memory Recalled",
  "memory.written": "Memory Written",
  "runtime.graph.interrupted": "Graph Interrupted",
  "runtime.graph.completed": "Graph Completed",
  "worker.health.reported": "Worker Health",
};

const workflowStatusToneMap: Record<WorkflowStatus, BadgeTone> = {
  created: "neutral",
  queued: "neutral",
  running: "info",
  waiting_approval: "warning",
  paused: "warning",
  retrying: "warning",
  completed: "success",
  failed: "danger",
  cancelled: "neutral",
};

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function workflowStatusTone(status: WorkflowStatus) {
  return workflowStatusToneMap[status];
}

export function workflowStatusLabel(status: WorkflowStatus) {
  return status.replaceAll("_", " ");
}

export function timelineItemViewModel(event: RunEvent) {
  const statusTone: BadgeTone = event.eventType.includes("failed")
    ? "danger"
    : event.eventType.includes("approval") || event.eventType.includes("retrying")
      ? "warning"
      : event.eventType.includes("completed")
        ? "success"
        : "info";

  return {
    ...event,
    label: eventLabelMap[event.eventType] ?? event.eventType,
    occurredAtLabel: formatTimestamp(event.occurredAt),
    summary:
      typeof event.payload.summary === "string"
        ? event.payload.summary
        : "No summary available for this runtime event.",
    statusTone,
    detailCode: JSON.stringify(event.payload, null, 2),
  };
}

export function graphNodeViewModel(node: TaskGraphNode, runId: string, projectId: string) {
  const status = node.status ?? "queued";
  const todoItems = node.todoItems ?? [];
  const completedTodoCount = todoItems.filter((item) => item.status === "completed").length;
  return {
    ...node,
    statusLabel: workflowStatusLabel((status === "queued" ? "queued" : status) as WorkflowStatus),
    statusTone:
      workflowStatusToneMap[
        ([
          "created",
          "queued",
          "running",
          "waiting_approval",
          "paused",
          "retrying",
          "completed",
          "failed",
          "cancelled",
        ].includes(status)
          ? status
          : "queued") as WorkflowStatus
      ],
    detailHref: `/runs/${runId}/tasks/${node.taskId}`,
    projectRunHref: `/projects/${projectId}/runs/${runId}`,
    todoItems,
    todoProgressLabel: todoItems.length
      ? `${completedTodoCount}/${todoItems.length} todo done`
      : "todo pending",
  };
}

export function taskAttemptViewModel(attempt: TaskAttempt, projectId: string, runId: string) {
  const status = (attempt.status ?? "queued") as WorkflowStatus;
  const attemptId = attempt.attemptId;
  return {
    ...attempt,
    startedAtLabel: attempt.startedAt ? formatTimestamp(attempt.startedAt) : "Not started",
    endedAtLabel: attempt.endedAt ? formatTimestamp(attempt.endedAt) : "In progress",
    statusLabel: workflowStatusLabel(status),
    statusTone: workflowStatusToneMap[status],
    opsHref: `/ops/attempts/${attemptId}`,
    projectRunHref: `/projects/${projectId}/runs/${runId}`,
  };
}

export function taskDetailViewModel(task: TaskDetailRecord) {
  const status = (task.status ?? "queued") as WorkflowStatus;
  const verificationTone: BadgeTone =
    task.verificationStatus === "passed"
      ? "success"
      : task.verificationStatus === "failed"
        ? "danger"
        : "warning";

  return {
    ...task,
    statusLabel: workflowStatusLabel(status),
    statusTone: workflowStatusToneMap[status],
    verificationTone,
    failureCategoryLabel: task.failureCategory ? task.failureCategory.replaceAll("_", " ") : "none",
    approvalHref: task.approvalId ? `/review/${task.approvalId}` : null,
    projectRunHref: `/projects/${task.projectId}/runs/${task.runId}`,
    artifactHrefs: task.linkedArtifactIds.map((artifactId) => ({
      artifactId,
      href: `/artifacts/${artifactId}`,
    })),
  };
}

export function spanViewModel(span: TraceSpanRecord) {
  const statusTone: BadgeTone =
    span.status === "ok" ? "success" : span.status === "error" ? "danger" : "warning";

  return {
    ...span,
    startedAtLabel: formatTimestamp(span.startedAt),
    endedAtLabel: formatTimestamp(span.endedAt),
    statusTone,
    depth: span.parentSpanId ? 1 : 0,
  };
}

export function traceViewModel(trace: TraceCorrelation) {
  return {
    ...trace,
    startedAtLabel: formatTimestamp(trace.startedAt),
    updatedAtLabel: formatTimestamp(trace.updatedAt),
    spans: trace.spans.map(spanViewModel),
  };
}

export function notificationViewModel(notification: NotificationSummary) {
  const statusTone: BadgeTone =
    notification.status === "delivered"
      ? "success"
      : notification.status === "failed"
        ? "danger"
        : "warning";

  return {
    ...notification,
    deliveredAtLabel: notification.deliveredAt
      ? formatTimestamp(notification.deliveredAt)
      : "Pending",
    statusTone,
  };
}

export function workerHealthViewModel(worker: WorkerHealthReadModel) {
  const statusTone: BadgeTone =
    worker.status === "healthy" ? "success" : worker.status === "unhealthy" ? "danger" : "warning";

  return {
    ...worker,
    lastSeenAtLabel: formatTimestamp(worker.lastSeenAt),
    statusTone,
  };
}

export function backlogViewModel(backlog: RuntimeBacklogSnapshot) {
  const lagTone: BadgeTone =
    backlog.eventLagSeconds > 60 ? "danger" : backlog.eventLagSeconds > 20 ? "warning" : "success";

  return {
    ...backlog,
    lastHeartbeatLabel: formatTimestamp(backlog.lastHeartbeatAt),
    lagTone,
  };
}
