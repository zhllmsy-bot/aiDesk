export const runtimeSchemaVersion = "2026-04-19.runtime.v1" as const;
export const runtimeTaskQueue = "ai-desk.runtime" as const;

export const workflowNames = [
  "project.import",
  "project.audit",
  "project.planning",
  "task.execution",
  "project.improvement",
] as const;

export const workflowRunStatuses = [
  "created",
  "queued",
  "running",
  "waiting_approval",
  "paused",
  "retrying",
  "completed",
  "failed",
  "cancelled",
] as const;

export const taskStatuses = [
  "queued",
  "claimed",
  "running",
  "verifying",
  "waiting_approval",
  "retrying",
  "completed",
  "failed",
  "reclaimed",
  "cancelled",
] as const;

export const approvalStatuses = [
  "pending",
  "approved",
  "rejected",
  "expired",
  "cancelled",
] as const;

export const claimStatuses = ["active", "released", "expired", "reclaimed"] as const;

export const graphKinds = ["auditor", "planner", "decomposition", "reviewer"] as const;

export const graphExecutionStatuses = ["completed", "interrupted"] as const;

export const workerHealthStatuses = ["healthy", "degraded", "unhealthy"] as const;

export const eventTypes = [
  "workflow.started",
  "workflow.completed",
  "workflow.failed",
  "workflow.retrying",
  "workflow.waiting_approval",
  "task.claimed",
  "task.running",
  "task.verifying",
  "task.completed",
  "task.failed",
  "task.heartbeat",
  "task.reclaimed",
  "task.graph.updated",
  "task.todo.updated",
  "approval.requested",
  "approval.resolved",
  "notification.sent",
  "artifact.linked",
  "memory.recalled",
  "memory.written",
  "runtime.graph.interrupted",
  "runtime.graph.completed",
  "worker.health.reported",
] as const;

export type WorkflowName = (typeof workflowNames)[number];
export type WorkflowRunStatus = (typeof workflowRunStatuses)[number];
export type TaskStatus = (typeof taskStatuses)[number];
export type ApprovalStatus = (typeof approvalStatuses)[number];
export type ClaimStatus = (typeof claimStatuses)[number];
export type GraphKind = (typeof graphKinds)[number];
export type GraphExecutionStatus = (typeof graphExecutionStatuses)[number];
export type WorkerHealthStatus = (typeof workerHealthStatuses)[number];
export type EventType = (typeof eventTypes)[number];
export type WorkflowStatus = WorkflowRunStatus;

export interface CorrelationIds {
  workflowRunId: string;
  traceId: string;
  workflowId?: string | null;
  projectId?: string | null;
  taskId?: string | null;
  attemptId?: string | null;
}

export interface RunEventEnvelope {
  eventId: string;
  eventType: EventType;
  schemaVersion: typeof runtimeSchemaVersion;
  payloadVersion: typeof runtimeSchemaVersion;
  sequence: number;
  producer: string;
  occurredAt: string;
  idempotencyKey: string;
  correlation: CorrelationIds;
  payload: Record<string, unknown>;
}
export type RunEvent = RunEventEnvelope;

export interface TimelineEntry {
  sequence: number;
  eventType: EventType;
  occurredAt: string;
  label: string;
  traceId: string;
  taskId?: string | null;
  attemptId?: string | null;
  summary?: string | null;
}

export interface TimelineReadModel {
  workflowRunId: string;
  entries: TimelineEntry[];
}

export interface TaskGraphNode {
  taskId: string;
  title: string;
  status?: TaskStatus | null;
  blockedReason?: string | null;
  executorSummary?: string | null;
  todoItems?: TaskTodoItem[];
}

export interface TaskTodoItem {
  id: string;
  title: string;
  status: "queued" | "running" | "completed" | "failed" | "skipped" | string;
  detail?: string | null;
}

export interface TaskGraphEdge {
  sourceTaskId: string;
  targetTaskId: string;
  kind: string;
}

export interface TaskGraphReadModel {
  workflowRunId: string;
  nodes: TaskGraphNode[];
  edges: TaskGraphEdge[];
}

export interface AttemptRecord {
  attemptId: string;
  taskId: string;
  status?: TaskStatus | WorkflowRunStatus | null;
  startedAt?: string | null;
  endedAt?: string | null;
  eventSequence: number[];
}
export type TaskAttempt = AttemptRecord;

export interface AttemptHistoryReadModel {
  taskId: string;
  attempts: AttemptRecord[];
}

export interface WorkerHealthReadModel {
  workerId: string;
  taskQueue: string;
  status: WorkerHealthStatus;
  lastSeenAt: string;
  activeWorkflowNames: WorkflowName[];
  detail?: string | null;
}

export interface NotificationSummary {
  notificationId: string;
  channel: "slack" | "email" | "webhook" | "in_app";
  status: "delivered" | "retrying" | "failed";
  target: string;
  summary: string;
  deliveredAt?: string | null;
  correlation: CorrelationIds;
}

export interface TraceSpanRecord {
  spanId: string;
  parentSpanId?: string | null;
  name: string;
  kind: "workflow" | "task" | "activity" | "tool" | "notification";
  status: "ok" | "warning" | "error";
  startedAt: string;
  endedAt: string;
  durationMs: number;
  summary?: string | null;
  correlation: CorrelationIds;
  attributes: Record<string, string>;
}

export interface TraceCorrelation {
  traceId: string;
  workflowRunId: string;
  workflowStatus: WorkflowRunStatus;
  rootSpanId: string;
  startedAt: string;
  updatedAt: string;
  spans: TraceSpanRecord[];
}

export interface RuntimeBacklogSnapshot {
  queueDepth: number;
  eventLagSeconds: number;
  waitingSignals: number;
  lastHeartbeatAt: string;
}
