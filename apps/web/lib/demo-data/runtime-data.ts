import type {
  NotificationSummary,
  RunEvent,
  RuntimeBacklogSnapshot,
  TaskAttempt,
  TaskGraphReadModel,
  TimelineReadModel,
  TraceCorrelation,
  TraceSpanRecord,
  WorkerHealthReadModel,
} from "@ai-desk/contracts-runtime";
import { runtimeSchemaVersion, runtimeTaskQueue } from "@ai-desk/contracts-runtime";

import type { RunRecord, RuntimeDataset, TaskDetailRecord } from "@/features/runs/types";

const run: RunRecord = {
  id: "run_20260419_main",
  projectId: "proj_meridian",
  projectName: "Meridian Control Plane",
  workflowName: "task.execution",
  workflowStatus: "waiting_approval",
  startedAt: "2026-04-19T00:39:00Z",
  updatedAt: "2026-04-19T00:47:00Z",
  statusReason: "Guarded workflow files changed, so execution is paused on a write approval.",
  currentTaskId: "task_patch_guard",
  currentTaskTitle: "Patch runtime retry guardrail",
  waitingForApproval: true,
  approvalId: "aprv_patch_guard",
};

const rawEvents: RunEvent[] = [
  {
    eventId: "evt_001",
    eventType: "workflow.started",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 1,
    producer: "runtime-worker",
    occurredAt: "2026-04-19T00:39:00Z",
    idempotencyKey: "run_20260419_main:1",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
    },
    payload: {
      summary: "Workflow started for guarded control-plane patch validation.",
    },
  },
  {
    eventId: "evt_002",
    eventType: "task.graph.updated",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 2,
    producer: "runtime-worker",
    occurredAt: "2026-04-19T00:39:10Z",
    idempotencyKey: "run_20260419_main:2",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
    },
    payload: {
      summary: "Task graph expanded with verification and approval edges.",
    },
  },
  {
    eventId: "evt_003",
    eventType: "task.todo.updated",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 3,
    producer: "runtime-worker",
    occurredAt: "2026-04-19T00:39:15Z",
    idempotencyKey: "run_20260419_main:3",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    payload: {
      summary: "Executor todo checklist emitted before implementation.",
      active_todo_id: "implement",
      todo_items: [
        { id: "context", title: "Assemble repo context and constraints", status: "completed" },
        { id: "plan", title: "Choose the implementation slice", status: "completed" },
        { id: "implement", title: "Apply code changes", status: "running" },
        { id: "verify", title: "Run required verification commands", status: "queued" },
        { id: "summarize", title: "Publish changed files and evidence", status: "queued" },
      ],
    },
  },
  {
    eventId: "evt_004",
    eventType: "task.claimed",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 4,
    producer: "codex-executor",
    occurredAt: "2026-04-19T00:39:20Z",
    idempotencyKey: "run_20260419_main:4",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    payload: {
      summary: "Executor claimed the guarded patch task.",
      to_status: "claimed",
      executor_summary: "codex-executor",
    },
  },
  {
    eventId: "evt_005",
    eventType: "task.running",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 5,
    producer: "codex-executor",
    occurredAt: "2026-04-19T00:40:10Z",
    idempotencyKey: "run_20260419_main:5",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    payload: {
      summary: "Patch bundle generated and dry-run verification started.",
      to_status: "running",
      executor_summary: "codex-executor / patch pipeline",
    },
  },
  {
    eventId: "evt_006",
    eventType: "artifact.linked",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 6,
    producer: "runtime-worker",
    occurredAt: "2026-04-19T00:42:00Z",
    idempotencyKey: "run_20260419_main:6",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    payload: {
      summary: "Patch diff and trace snapshot linked to the current attempt.",
    },
  },
  {
    eventId: "evt_007",
    eventType: "task.verifying",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 7,
    producer: "verification-runner",
    occurredAt: "2026-04-19T00:42:40Z",
    idempotencyKey: "run_20260419_main:7",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    payload: {
      summary: "Verification passed syntax checks but touched protected workflow paths.",
      to_status: "verifying",
    },
  },
  {
    eventId: "evt_008",
    eventType: "approval.requested",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 8,
    producer: "review-domain",
    occurredAt: "2026-04-19T00:43:05Z",
    idempotencyKey: "run_20260419_main:8",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    payload: {
      summary: "Approval requested for guarded workflow control-plane files.",
    },
  },
  {
    eventId: "evt_009",
    eventType: "workflow.waiting_approval",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 9,
    producer: "runtime-worker",
    occurredAt: "2026-04-19T00:43:10Z",
    idempotencyKey: "run_20260419_main:9",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    payload: {
      summary: "Workflow paused pending human approval.",
      blocked_reason: "Protected files require manual approval.",
    },
  },
  {
    eventId: "evt_010",
    eventType: "notification.sent",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 10,
    producer: "notification-worker",
    occurredAt: "2026-04-19T00:43:20Z",
    idempotencyKey: "run_20260419_main:10",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    payload: {
      summary: "Slack notification sent to release-ops channel.",
    },
  },
  {
    eventId: "evt_011",
    eventType: "worker.health.reported",
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: 11,
    producer: "runtime-worker",
    occurredAt: "2026-04-19T00:47:00Z",
    idempotencyKey: "run_20260419_main:11",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
    },
    payload: {
      worker_id: "worker-runtime-a",
      task_queue: runtimeTaskQueue,
      status: "healthy",
      active_workflow_names: ["task.execution"],
      detail: "Awaiting approval response; worker heartbeat remains healthy.",
      summary: "Worker heartbeat updated while workflow waits for signal.",
    },
  },
];

const timeline: TimelineReadModel = {
  workflowRunId: run.id,
  entries: rawEvents.map((event) => ({
    sequence: event.sequence,
    eventType: event.eventType,
    occurredAt: event.occurredAt,
    label: event.eventType.replaceAll(".", " "),
    traceId: event.correlation.traceId,
    taskId: event.correlation.taskId ?? null,
    attemptId: event.correlation.attemptId ?? null,
    summary: typeof event.payload.summary === "string" ? event.payload.summary : null,
  })),
};

const graph: TaskGraphReadModel = {
  workflowRunId: run.id,
  nodes: [
    {
      taskId: "task_prepare_patch",
      title: "Prepare patch scope",
      status: "completed",
      executorSummary: "planner / decomposition graph",
    },
    {
      taskId: "task_patch_guard",
      title: "Patch runtime retry guardrail",
      status: "waiting_approval",
      blockedReason: "Protected files require manual approval.",
      executorSummary: "codex-executor / patch pipeline",
      todoItems: [
        {
          id: "context",
          title: "Assemble repo context and constraints",
          status: "completed",
          detail: "Loaded workflow scope, policy gate, and verification expectations.",
        },
        {
          id: "plan",
          title: "Choose the implementation slice",
          status: "completed",
          detail: "Selected the retry guardrail as the smallest shippable change.",
        },
        {
          id: "implement",
          title: "Apply code changes",
          status: "completed",
          detail: "Patch was generated and linked as runtime evidence.",
        },
        {
          id: "verify",
          title: "Run required verification commands",
          status: "running",
          detail: "Verification paused when protected workflow paths required approval.",
        },
        {
          id: "summarize",
          title: "Publish changed files and evidence",
          status: "queued",
          detail: "Waiting for approval resolution before final summary.",
        },
      ],
    },
    {
      taskId: "task_verify_guard",
      title: "Replay verification and trace correlation",
      status: "queued",
      executorSummary: "verification-runner",
    },
  ],
  edges: [
    {
      sourceTaskId: "task_prepare_patch",
      targetTaskId: "task_patch_guard",
      kind: "depends_on",
    },
    {
      sourceTaskId: "task_patch_guard",
      targetTaskId: "task_verify_guard",
      kind: "depends_on",
    },
  ],
};

const attemptsByTaskId: Record<string, TaskAttempt[]> = {
  task_patch_guard: [
    {
      attemptId: "att_patch_001",
      taskId: "task_patch_guard",
      status: "failed",
      startedAt: "2026-04-19T00:28:00Z",
      endedAt: "2026-04-19T00:35:00Z",
      eventSequence: [1, 2, 3],
    },
    {
      attemptId: "att_patch_002",
      taskId: "task_patch_guard",
      status: "waiting_approval",
      startedAt: "2026-04-19T00:39:20Z",
      endedAt: null,
      eventSequence: [3, 4, 5, 6, 7, 8, 9, 10],
    },
  ],
};

const taskDetails: Record<string, TaskDetailRecord> = {
  task_patch_guard: {
    runId: run.id,
    taskId: "task_patch_guard",
    projectId: run.projectId,
    title: "Patch runtime retry guardrail",
    description:
      "Adjust retry timing in the workflow dispatcher without breaking approval or telemetry semantics.",
    executor: "codex-executor",
    status: "waiting_approval",
    acceptanceCriteria: [
      "Retry window update is reflected in runtime control-plane code.",
      "Timeline and telemetry still correlate through the same trace envelope.",
      "Protected file writes stay behind manual approval.",
    ],
    verificationSummary:
      "Dry-run patch applied and verification completed, but protected workflow files require operator review.",
    verificationStatus: "warning",
    retryCount: 1,
    failureCategory: "policy_gate",
    failureReason: "Attempt paused by protected-path write policy.",
    waitingApprovalReason:
      "Workflow dispatch and retry policy files sit behind a manual write gate.",
    blockedReason: "Awaiting approval resolution from review lane.",
    linkedArtifactIds: ["art_patch_guard", "art_trace_guard", "art_dashboard_shot"],
    approvalId: "aprv_patch_guard",
  },
};

const spans: TraceSpanRecord[] = [
  {
    spanId: "span_root",
    name: "run.dispatch",
    kind: "workflow",
    status: "warning",
    startedAt: "2026-04-19T00:39:00Z",
    endedAt: "2026-04-19T00:47:00Z",
    durationMs: 480000,
    summary: "Workflow paused at approval gate.",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
    },
    attributes: {
      queue: runtimeTaskQueue,
      workflowStatus: run.workflowStatus,
    },
  },
  {
    spanId: "span_patch",
    parentSpanId: "span_root",
    name: "executor.apply_patch",
    kind: "task",
    status: "warning",
    startedAt: "2026-04-19T00:40:10Z",
    endedAt: "2026-04-19T00:42:00Z",
    durationMs: 110000,
    summary: "Patch generated and diff attached.",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    attributes: {
      executor: "codex-executor",
      artifactCount: "3",
    },
  },
  {
    spanId: "span_verify",
    parentSpanId: "span_root",
    name: "verification.replay_trace",
    kind: "activity",
    status: "ok",
    startedAt: "2026-04-19T00:42:00Z",
    endedAt: "2026-04-19T00:42:45Z",
    durationMs: 45000,
    summary: "Replay fetched spans and validated correlation IDs.",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    attributes: {
      spansFetched: "242",
      cacheHit: "true",
    },
  },
  {
    spanId: "span_notify",
    parentSpanId: "span_root",
    name: "notification.slack",
    kind: "notification",
    status: "ok",
    startedAt: "2026-04-19T00:43:12Z",
    endedAt: "2026-04-19T00:43:20Z",
    durationMs: 8000,
    summary: "Slack notification delivered to release-ops.",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    attributes: {
      channel: "slack",
      target: "#release-ops",
    },
  },
];

const trace: TraceCorrelation = {
  traceId: "trace_patch_guard",
  workflowRunId: run.id,
  workflowStatus: run.workflowStatus,
  rootSpanId: "span_root",
  startedAt: "2026-04-19T00:39:00Z",
  updatedAt: "2026-04-19T00:47:00Z",
  spans,
};

const notifications: NotificationSummary[] = [
  {
    notificationId: "notif_patch_guard",
    channel: "slack",
    status: "delivered",
    target: "#release-ops",
    summary: "Approval required for guarded workflow patch.",
    deliveredAt: "2026-04-19T00:43:20Z",
    correlation: {
      workflowRunId: run.id,
      traceId: "trace_patch_guard",
      projectId: run.projectId,
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
  },
];

const workers: WorkerHealthReadModel[] = [
  {
    workerId: "worker-runtime-a",
    taskQueue: runtimeTaskQueue,
    status: "healthy",
    lastSeenAt: "2026-04-19T00:47:00Z",
    activeWorkflowNames: ["task.execution", "project.planning"],
    detail: "Heartbeat received while workflow waits for signal.",
  },
  {
    workerId: "worker-verify-b",
    taskQueue: "ai-desk.verify",
    status: "degraded",
    lastSeenAt: "2026-04-19T00:46:20Z",
    activeWorkflowNames: ["task.execution"],
    detail: "Backlog rising because approval-gated runs are accumulating replay jobs.",
  },
];

const backlog: RuntimeBacklogSnapshot = {
  queueDepth: 7,
  eventLagSeconds: 19,
  waitingSignals: 2,
  lastHeartbeatAt: "2026-04-19T00:47:00Z",
};

const dataset: RuntimeDataset = {
  run,
  events: rawEvents,
  timeline,
  graph,
  attemptsByTaskId,
  taskDetails,
  trace,
  notifications,
  workers,
  backlog,
};

export function listRunFixtures() {
  return [structuredClone(dataset.run)];
}

export function getRuntimeDataset(runId: string) {
  if (runId !== dataset.run.id) {
    return null;
  }

  return structuredClone(dataset);
}

export function getRunRecord(runId: string) {
  return runId === dataset.run.id ? structuredClone(dataset.run) : null;
}

export function listRunEvents(runId: string) {
  return runId === dataset.run.id ? structuredClone(rawEvents) : [];
}

export function getTimelineFixture(runId: string) {
  return runId === dataset.run.id ? structuredClone(dataset.timeline) : null;
}

export function getTaskGraphFixture(runId: string) {
  return runId === dataset.run.id ? structuredClone(dataset.graph) : null;
}

export function getTaskAttemptsFixture(runId: string, taskId: string) {
  if (runId !== dataset.run.id) {
    return [];
  }

  return structuredClone(dataset.attemptsByTaskId[taskId] ?? []);
}

export function getTaskDetailFixture(runId: string, taskId: string) {
  if (runId !== dataset.run.id) {
    return null;
  }

  return structuredClone(dataset.taskDetails[taskId] ?? null);
}

export function getTraceFixture(runId: string) {
  return runId === dataset.run.id ? structuredClone(dataset.trace) : null;
}

export function getNotificationsFixture(runId: string) {
  return runId === dataset.run.id ? structuredClone(dataset.notifications) : [];
}

export function listWorkerHealthFixtures() {
  return structuredClone(dataset.workers);
}

export function getRuntimeBacklogFixture(runId: string) {
  return runId === dataset.run.id ? structuredClone(dataset.backlog) : null;
}
