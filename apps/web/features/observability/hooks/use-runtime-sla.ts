"use client";

import { useQuery } from "@tanstack/react-query";

import { runKeys } from "@/lib/query-keys";

import { type RuntimeSlaQuery, getRuntimeSla } from "../api/get-runtime-sla";

type UseRuntimeSlaQuery = RuntimeSlaQuery & {
  enabled?: boolean;
};

export function useRuntimeSla(query: UseRuntimeSlaQuery = {}) {
  const { enabled = true, ...runtimeSlaQuery } = query;
  const bucketMinutes = runtimeSlaQuery.bucketMinutes ?? 60;
  const windowHours = runtimeSlaQuery.windowHours ?? 24 * 7;

  return useQuery({
    queryKey: runKeys.runtimeSla(
      runtimeSlaQuery.projectId,
      runtimeSlaQuery.iterationId,
      bucketMinutes,
      windowHours,
    ),
    queryFn: () => getRuntimeSla(runtimeSlaQuery),
    enabled,
  });
}
