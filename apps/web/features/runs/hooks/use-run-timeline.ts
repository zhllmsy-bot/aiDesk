"use client";

import { useQuery } from "@tanstack/react-query";

import { runKeys } from "@/lib/query-keys";

import { getRunTimeline } from "../api/get-run-timeline";

export function useRunTimeline(runId: string) {
  return useQuery({
    queryKey: runKeys.timeline(runId),
    queryFn: () => getRunTimeline(runId),
  });
}
