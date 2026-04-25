"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Input, Panel, StatusBadge } from "@ai-desk/ui";

const pinnedRuns = [
  {
    id: "run-childlearn-self-20260424142059",
    label: "childLearn self-iteration",
    status: "running",
    description: "Current autonomous product iteration with subagent TODO monitoring.",
  },
  {
    id: "run_20260419_main",
    label: "runtime fixture",
    status: "waiting approval",
    description: "Built-in sample run for timeline, task graph, and review flows.",
  },
];

export function RunsIndexScreen() {
  const router = useRouter();
  const [runId, setRunId] = useState("");

  return (
    <div className="page-stack">
      <Panel eyebrow="Runs" title="Open a run command surface">
        <div className="run-command-grid">
          <form
            className="run-command-main"
            onSubmit={(event) => {
              event.preventDefault();
              const trimmedRunId = runId.trim();
              if (trimmedRunId) {
                router.push(`/runs/${encodeURIComponent(trimmedRunId)}/timeline`);
              }
            }}
          >
            <p className="run-lead">
              Autonomous runs stay inspectable by status, subagent checklist, event log, and
              evidence without hunting through backend traces.
            </p>
            <div className="run-lookup-form">
              <Input
                aria-label="Run ID"
                value={runId}
                onChange={(event) => setRunId(event.target.value)}
                placeholder="run-childlearn-self-20260424142059"
              />
              <Button type="submit">Open run</Button>
            </div>
          </form>

          <div className="run-command-todos">
            <div className="ui-eyebrow">Pinned views</div>
            {pinnedRuns.map((run) => (
              <Link key={run.id} className="run-todo-row" href={`/runs/${run.id}/timeline`}>
                <StatusBadge
                  label={run.status}
                  tone={run.status === "running" ? "info" : "warning"}
                />
                <div>
                  <strong>{run.label}</strong>
                  <p className="ui-copy">{run.description}</p>
                  <div className="run-todo-muted">{run.id}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </Panel>
    </div>
  );
}
