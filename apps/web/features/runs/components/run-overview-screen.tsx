"use client";

import Link from "next/link";

import { Button, Panel, StatusBadge } from "@ai-desk/ui";

import { getRunRecord } from "../fixtures/runtime-data";
import { useRunEvents } from "../hooks/use-run-events";
import { useTaskGraph } from "../hooks/use-task-graph";
import type { RunRecord } from "../types";
import {
  timelineItemViewModel,
  workflowStatusLabel,
  workflowStatusTone,
} from "../view-models/runtime-view-models";
import { RunTimelinePanel } from "./run-timeline-panel";
import { TaskGraphPanel } from "./task-graph-panel";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const activeTaskStatuses = new Set([
  "claimed",
  "running",
  "verifying",
  "waiting_approval",
  "retrying",
]);

const statusToneByTaskStatus: Record<string, BadgeTone> = {
  queued: "neutral",
  claimed: "info",
  running: "info",
  verifying: "warning",
  waiting_approval: "warning",
  retrying: "warning",
  completed: "success",
  failed: "danger",
  cancelled: "neutral",
  reclaimed: "warning",
};

const todoToneByStatus: Record<string, BadgeTone> = {
  queued: "neutral",
  running: "info",
  completed: "success",
  failed: "danger",
  skipped: "warning",
};

function readableStatus(value: string) {
  return value.replaceAll("_", " ");
}

function shortId(value: string) {
  const parts = value.split("::");
  const tail = parts.at(-1) ?? value;
  return tail.length > 36 ? `${tail.slice(0, 17)}...${tail.slice(-12)}` : tail;
}

function formatClock(value?: string | null) {
  if (!value) {
    return "No timestamp";
  }

  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function RunCommandPanel({
  runId,
  run,
  projectId,
}: {
  runId: string;
  run: RunRecord | null;
  projectId: string;
}) {
  const graphQuery = useTaskGraph(runId);
  const eventsQuery = useRunEvents(runId);
  const nodes = graphQuery.data?.nodes ?? [];
  const activeNode =
    nodes.find((node) => run?.currentTaskId && node.taskId === run.currentTaskId) ??
    nodes.find((node) => activeTaskStatuses.has(node.status ?? "")) ??
    nodes.find((node) => node.status !== "completed") ??
    nodes.at(-1) ??
    null;
  const events = (eventsQuery.data ?? []).map(timelineItemViewModel);
  const latestEvent = events.at(-1) ?? null;
  const todoItems = activeNode?.todoItems ?? [];
  const completedTodoCount = todoItems.filter((item) => item.status === "completed").length;
  const activeTodo =
    todoItems.find((item) => item.status === "running") ??
    todoItems.find((item) => item.status === "queued") ??
    null;
  const nextTodo = todoItems.find((item) => item.status === "queued" && item.id !== activeTodo?.id);
  const taskStatus = activeNode?.status ?? run?.workflowStatus ?? "running";
  const statusLabel = run ? workflowStatusLabel(run.workflowStatus) : readableStatus(taskStatus);
  const statusTone = run
    ? workflowStatusTone(run.workflowStatus)
    : (statusToneByTaskStatus[taskStatus] ?? "info");
  const activeTaskTitle = activeNode?.title ?? run?.currentTaskTitle ?? "Waiting for graph";
  const lead =
    run?.statusReason ??
    latestEvent?.summary ??
    activeNode?.executorSummary ??
    (activeNode?.blockedReason ? `Blocked by ${shortId(activeNode.blockedReason)}` : null) ??
    "Live runtime data is available. The graph and event log below are pulled from backend read models.";

  return (
    <Panel
      eyebrow="Run command"
      title={run ? `${run.projectName} / ${shortId(runId)}` : shortId(runId)}
      actions={
        <div className="inline-actions">
          {run ? (
            <Link href={`/projects/${run.projectId}`}>
              <Button tone="ghost">Project</Button>
            </Link>
          ) : null}
          {activeNode ? (
            <Link href={`/runs/${runId}/tasks/${activeNode.taskId}`}>
              <Button tone="secondary">Task</Button>
            </Link>
          ) : null}
          <Link href={`/runs/${runId}/telemetry`}>
            <Button>Telemetry</Button>
          </Link>
        </div>
      }
    >
      <div className="run-command-grid">
        <div className="run-command-main">
          <div className="inline-actions">
            <StatusBadge label={statusLabel} tone={statusTone} />
            <StatusBadge
              label={graphQuery.isLoading ? "graph loading" : "graph live"}
              tone="info"
            />
            <StatusBadge
              label={eventsQuery.isLoading ? "events loading" : "events live"}
              tone="info"
            />
          </div>
          <p className="run-lead">{lead}</p>
          <div className="signal-strip">
            <div className="signal-cell">
              <span>Current task</span>
              <strong>{activeTaskTitle}</strong>
              <code className="graph-task-id">
                {activeNode?.taskId
                  ? shortId(activeNode.taskId)
                  : (run?.currentTaskId ?? "pending")}
              </code>
            </div>
            <div className="signal-cell">
              <span>Checklist</span>
              <strong>
                {todoItems.length ? `${completedTodoCount}/${todoItems.length}` : "pending"}
              </strong>
              <code className="graph-task-id">{activeTodo?.title ?? "No active todo yet"}</code>
            </div>
            <div className="signal-cell">
              <span>Latest event</span>
              <strong>{latestEvent?.label ?? "Waiting for event"}</strong>
              <code className="graph-task-id">
                {latestEvent
                  ? `${formatClock(latestEvent.occurredAt)} / #${latestEvent.sequence}`
                  : "pending"}
              </code>
            </div>
          </div>
        </div>

        <div className="run-command-todos">
          <div className="task-todo-header">
            <span>Subagent checklist</span>
            <span>
              {todoItems.length ? `${completedTodoCount}/${todoItems.length}` : "pending"}
            </span>
          </div>
          {activeTodo ? (
            <div className="run-todo-row">
              <StatusBadge
                label={activeTodo.status}
                tone={todoToneByStatus[activeTodo.status] ?? "neutral"}
              />
              <div>
                <strong>{activeTodo.title}</strong>
                <p className="ui-copy">
                  {activeTodo.detail ?? "Executor is expected to update this item as it moves."}
                </p>
              </div>
            </div>
          ) : (
            <div className="surface-note">
              No live todo item has been emitted for this task yet.
            </div>
          )}
          <div className="run-todo-muted">
            Next: {nextTodo?.title ?? "waiting on the active agent"}
          </div>
          {run?.waitingForApproval && run.approvalId ? (
            <Link href={`/review/${run.approvalId}`}>
              <Button tone="secondary">Open approval</Button>
            </Link>
          ) : null}
          {run ? (
            <Link href={`/projects/${projectId}/runs/${runId}`}>
              <Button tone="ghost">Project run view</Button>
            </Link>
          ) : null}
        </div>
      </div>
    </Panel>
  );
}

export function RunOverviewScreen({ runId }: { runId: string }) {
  const run = getRunRecord(runId);
  const projectId = run?.projectId ?? "runtime";

  if (!run) {
    return (
      <div className="page-stack">
        <RunCommandPanel runId={runId} run={null} projectId={projectId} />

        <div className="split-grid">
          <RunTimelinePanel runId={runId} projectId={projectId} />
          <TaskGraphPanel runId={runId} projectId={projectId} />
        </div>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <RunCommandPanel runId={runId} run={run} projectId={projectId} />

      <div className="split-grid">
        <RunTimelinePanel runId={runId} projectId={projectId} />
        <TaskGraphPanel runId={runId} projectId={projectId} />
      </div>
    </div>
  );
}
