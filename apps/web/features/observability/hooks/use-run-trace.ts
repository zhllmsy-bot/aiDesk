"use client";

import { useQuery } from "@tanstack/react-query";

import { getTraceFixture } from "@/lib/demo-data/runtime-data";
import { runKeys } from "@/lib/query-keys";

export function useRunTrace(runId: string) {
  return useQuery({
    queryKey: runKeys.trace(runId),
    queryFn: async () => {
      await new Promise((resolve) => setTimeout(resolve, 40));
      const trace = getTraceFixture(runId);
      if (!trace) {
        throw new Error(`Trace ${runId} not found`);
      }
      return trace;
    },
  });
}
