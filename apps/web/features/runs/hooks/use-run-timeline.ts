"use client";

import { useQuery } from "@tanstack/react-query";

import { getRunTimeline } from "../api/get-run-timeline";

export const runKeys = {
  all: ["runs"] as const,
  timeline: (runId: string) => [...runKeys.all, "timeline", runId] as const,
  events: (runId: string) => [...runKeys.all, "events", runId] as const,
  graph: (runId: string) => [...runKeys.all, "graph", runId] as const,
  taskDetail: (runId: string, taskId: string) =>
    [...runKeys.all, "task-detail", runId, taskId] as const,
  attempts: (runId: string, taskId: string) => [...runKeys.all, "attempts", runId, taskId] as const,
  trace: (runId: string) => [...runKeys.all, "trace", runId] as const,
  notifications: (runId: string) => [...runKeys.all, "notifications", runId] as const,
  workers: () => [...runKeys.all, "workers"] as const,
  backlog: (runId: string) => [...runKeys.all, "backlog", runId] as const,
  runtimeSla: (
    projectId?: string,
    iterationId?: string,
    bucketMinutes = 60,
    windowHours = 24 * 7,
  ) =>
    [
      ...runKeys.all,
      "runtime-sla",
      projectId ?? "all-projects",
      iterationId ?? "all-iterations",
      bucketMinutes,
      windowHours,
    ] as const,
};

export function useRunTimeline(runId: string) {
  return useQuery({
    queryKey: runKeys.timeline(runId),
    queryFn: () => getRunTimeline(runId),
  });
}
