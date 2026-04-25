import type {
  EventType,
  RunEvent,
  TaskAttempt,
  TaskGraphReadModel,
  TimelineReadModel,
} from "@ai-desk/contracts-runtime";
import { runtimeSchemaVersion } from "@ai-desk/contracts-runtime";

import { getApiErrorMessage, getApiHeaders } from "@/lib/api-client";

import type { TaskDetailRecord } from "../types";

type RawTodoItem = {
  id: string;
  title: string;
  status: string;
  detail?: string | null;
};

type RawTaskGraphNode = {
  task_id: string;
  title: string;
  status?: string | null;
  blocked_reason?: string | null;
  executor_summary?: string | null;
  todo_items?: RawTodoItem[];
};

type RawTaskGraphReadModel = {
  workflow_run_id: string;
  nodes?: RawTaskGraphNode[];
  edges?: {
    source_task_id: string;
    target_task_id: string;
    kind: string;
  }[];
};

type RawTimelineReadModel = {
  workflow_run_id: string;
  entries?: {
    sequence: number;
    event_type: string;
    occurred_at: string;
    label: string;
    trace_id: string;
    task_id?: string | null;
    attempt_id?: string | null;
    summary?: string | null;
  }[];
};

type RawAttemptHistoryReadModel = {
  task_id: string;
  attempts?: {
    attempt_id: string;
    task_id: string;
    status?: string | null;
    started_at?: string | null;
    ended_at?: string | null;
    event_sequence?: number[];
  }[];
};

async function fetchRuntimeJson(path: string): Promise<unknown> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const response = await fetch(`${baseUrl}${path}`, {
    method: "GET",
    headers: await getApiHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new Error(getApiErrorMessage(payload, response.status));
  }

  return response.json();
}

function mapTaskGraph(raw: RawTaskGraphReadModel): TaskGraphReadModel {
  return {
    workflowRunId: raw.workflow_run_id,
    nodes: (raw.nodes ?? []).map((node) => ({
      taskId: node.task_id,
      title: node.title,
      status: node.status as TaskGraphReadModel["nodes"][number]["status"],
      blockedReason: node.blocked_reason,
      executorSummary: node.executor_summary,
      todoItems: (node.todo_items ?? []).map((item) => ({
        id: item.id,
        title: item.title,
        status: item.status,
        detail: item.detail,
      })),
    })),
    edges: (raw.edges ?? []).map((edge) => ({
      sourceTaskId: edge.source_task_id,
      targetTaskId: edge.target_task_id,
      kind: edge.kind,
    })),
  };
}

function mapTimeline(raw: RawTimelineReadModel): TimelineReadModel {
  return {
    workflowRunId: raw.workflow_run_id,
    entries: (raw.entries ?? []).map((entry) => ({
      sequence: entry.sequence,
      eventType: entry.event_type as EventType,
      occurredAt: entry.occurred_at,
      label: entry.label,
      traceId: entry.trace_id,
      taskId: entry.task_id,
      attemptId: entry.attempt_id,
      summary: entry.summary,
    })),
  };
}

function mapAttempts(raw: RawAttemptHistoryReadModel): TaskAttempt[] {
  return (raw.attempts ?? []).map((attempt) => ({
    attemptId: attempt.attempt_id,
    taskId: attempt.task_id,
    status: attempt.status as TaskAttempt["status"],
    startedAt: attempt.started_at,
    endedAt: attempt.ended_at,
    eventSequence: attempt.event_sequence ?? [],
  }));
}

export async function fetchTaskGraphLive(runId: string): Promise<TaskGraphReadModel> {
  const raw = (await fetchRuntimeJson(
    `/runtime/runs/${encodeURIComponent(runId)}/graph`,
  )) as RawTaskGraphReadModel;
  return mapTaskGraph(raw);
}

export async function fetchTimelineLive(runId: string): Promise<TimelineReadModel> {
  const raw = (await fetchRuntimeJson(
    `/runtime/runs/${encodeURIComponent(runId)}/timeline`,
  )) as RawTimelineReadModel;
  return mapTimeline(raw);
}

export async function fetchRunEventsLive(runId: string): Promise<RunEvent[]> {
  const timeline = await fetchTimelineLive(runId);
  return timeline.entries.map((entry) => ({
    eventId: `${runId}:${entry.sequence}`,
    eventType: entry.eventType,
    schemaVersion: runtimeSchemaVersion,
    payloadVersion: runtimeSchemaVersion,
    sequence: entry.sequence,
    producer: "runtime.timeline",
    occurredAt: entry.occurredAt,
    idempotencyKey: `${runId}:${entry.sequence}:${entry.eventType}`,
    correlation: {
      workflowRunId: runId,
      traceId: entry.traceId,
      taskId: entry.taskId,
      attemptId: entry.attemptId,
    },
    payload: {
      label: entry.label,
      summary: entry.summary,
    },
  }));
}

export async function fetchTaskAttemptsLive(
  _runId: string,
  taskId: string,
): Promise<TaskAttempt[]> {
  const raw = (await fetchRuntimeJson(
    `/runtime/tasks/${encodeURIComponent(taskId)}/attempts`,
  )) as RawAttemptHistoryReadModel;
  return mapAttempts(raw);
}

export async function fetchTaskDetailLive(
  runId: string,
  taskId: string,
): Promise<TaskDetailRecord> {
  const [graph, attempts] = await Promise.all([
    fetchTaskGraphLive(runId),
    fetchTaskAttemptsLive(runId, taskId).catch(() => []),
  ]);
  const node = graph.nodes.find((candidate) => candidate.taskId === taskId);
  if (!node) {
    throw new Error(`Task detail ${taskId} not found in run ${runId}`);
  }

  const latestAttempt = attempts.at(-1);
  const status = node.status ?? latestAttempt?.status ?? "queued";
  const failed = status === "failed" || status === "cancelled" || status === "reclaimed";
  const completed = status === "completed";
  const todoTitles = (node.todoItems ?? []).map((item) => `${item.status}: ${item.title}`);

  return {
    runId,
    taskId,
    projectId: "runtime",
    title: node.title,
    description:
      node.blockedReason ??
      node.executorSummary ??
      "Live runtime task projected from the execution graph.",
    executor: node.executorSummary ?? "runtime worker",
    status,
    acceptanceCriteria: todoTitles.length ? todoTitles : ["Runtime task checklist pending."],
    verificationSummary: completed
      ? "Runtime task reached completed state."
      : failed
        ? "Runtime task ended before successful verification."
        : "Runtime task is still in progress or waiting for its dependency.",
    verificationStatus: completed ? "passed" : failed ? "failed" : "warning",
    retryCount: Math.max(0, attempts.length - 1),
    failureCategory: failed ? "runtime" : "none",
    failureReason: failed ? node.blockedReason : null,
    waitingApprovalReason: null,
    blockedReason: node.blockedReason,
    linkedArtifactIds: [],
    approvalId: null,
  };
}
