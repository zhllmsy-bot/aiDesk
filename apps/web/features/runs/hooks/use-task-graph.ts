"use client";

import { useQuery } from "@tanstack/react-query";

import { runKeys } from "@/lib/query-keys";

import { getTaskGraph } from "../api/get-task-graph";

export function useTaskGraph(runId: string) {
  return useQuery({
    queryKey: runKeys.graph(runId),
    queryFn: () => getTaskGraph(runId),
  });
}
