"use client";

import { useQuery } from "@tanstack/react-query";

import { runKeys } from "@/lib/query-keys";

import { getRunEvents } from "../api/get-run-events";

export function useRunEvents(runId: string) {
  return useQuery({
    queryKey: runKeys.events(runId),
    queryFn: () => getRunEvents(runId),
  });
}
