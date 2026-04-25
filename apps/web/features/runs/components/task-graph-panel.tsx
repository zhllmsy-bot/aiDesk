"use client";

import Link from "next/link";

import { Button, Panel, StatusBadge } from "@ai-desk/ui";

import { graphNodeViewModel } from "@/lib/view-models/runtime-view-models";
import { useTaskGraph } from "../hooks/use-task-graph";

const todoToneByStatus = {
  queued: "neutral",
  running: "info",
  completed: "success",
  failed: "danger",
  skipped: "warning",
} as const;

function shortId(value: string) {
  const parts = value.split("::");
  const tail = parts.at(-1) ?? value;
  return tail.length > 36 ? `${tail.slice(0, 17)}...${tail.slice(-12)}` : tail;
}

export function TaskGraphPanel({
  runId,
  projectId,
}: {
  runId: string;
  projectId: string;
}) {
  const { data, isLoading } = useTaskGraph(runId);

  if (isLoading || !data) {
    return (
      <Panel eyebrow="Agent plan" title="Task checklist">
        <div className="surface-note">Loading graph layout...</div>
      </Panel>
    );
  }

  const nodes = data.nodes.map((node) => graphNodeViewModel(node, runId, projectId));

  return (
    <Panel eyebrow="Agent plan" title="Subagent execution plan">
      <ul className="graph-grid" aria-label="Task graph">
        {nodes.map((node) => {
          const inbound = data.edges.filter((edge) => edge.targetTaskId === node.taskId);
          const outbound = data.edges.filter((edge) => edge.sourceTaskId === node.taskId);

          return (
            <li key={node.taskId} className="graph-node-card">
              <div className="list-card-header">
                <div>
                  <h3>{node.title}</h3>
                  <div className="graph-task-id" title={node.taskId}>
                    {shortId(node.taskId)}
                  </div>
                </div>
                <StatusBadge label={node.statusLabel} tone={node.statusTone} />
              </div>
              <p className="ui-copy">
                {node.blockedReason ?? node.executorSummary ?? "No blocking note for this task."}
              </p>
              {node.todoItems.length ? (
                <div className="task-todo-list" aria-label={`${node.title} todo list`}>
                  <div className="task-todo-header">
                    <span>Agent todo</span>
                    <span>{node.todoProgressLabel}</span>
                  </div>
                  <ol>
                    {node.todoItems.map((item) => (
                      <li key={item.id} className={`task-todo-item is-${item.status}`}>
                        <StatusBadge
                          label={item.status}
                          tone={
                            todoToneByStatus[item.status as keyof typeof todoToneByStatus] ??
                            "neutral"
                          }
                        />
                        <div>
                          <strong>{item.title}</strong>
                          {item.detail ? <p className="ui-copy">{item.detail}</p> : null}
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              ) : (
                <div className="surface-note">No subagent todo emitted yet.</div>
              )}
              <div className="meta-row">
                <span>
                  depends on:{" "}
                  {inbound.map((edge) => shortId(edge.sourceTaskId)).join(", ") || "none"}
                </span>
                <span>
                  unblocks:{" "}
                  {outbound.map((edge) => shortId(edge.targetTaskId)).join(", ") || "none"}
                </span>
              </div>
              <div className="inline-actions">
                <Link href={node.detailHref}>
                  <Button>Inspect task</Button>
                </Link>
                <Link href={node.projectRunHref}>
                  <Button tone="secondary">Project run</Button>
                </Link>
              </div>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
