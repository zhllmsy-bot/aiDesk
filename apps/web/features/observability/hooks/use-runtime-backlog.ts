"use client";

import { useQuery } from "@tanstack/react-query";

import { getRuntimeBacklogFixture } from "@/lib/demo-data/runtime-data";
import { runKeys } from "@/lib/query-keys";

export function useRuntimeBacklog(runId: string) {
  return useQuery({
    queryKey: runKeys.backlog(runId),
    queryFn: async () => {
      await new Promise((resolve) => setTimeout(resolve, 40));
      return getRuntimeBacklogFixture(runId);
    },
  });
}
