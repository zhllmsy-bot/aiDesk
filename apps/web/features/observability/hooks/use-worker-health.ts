"use client";

import { useQuery } from "@tanstack/react-query";

import { listWorkerHealthFixtures } from "@/lib/demo-data/runtime-data";
import { runKeys } from "@/lib/query-keys";

export function useWorkerHealth() {
  return useQuery({
    queryKey: runKeys.workers(),
    queryFn: async () => {
      await new Promise((resolve) => setTimeout(resolve, 40));
      return listWorkerHealthFixtures();
    },
  });
}
