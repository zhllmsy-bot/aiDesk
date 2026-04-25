"use client";

import { useQuery } from "@tanstack/react-query";

import { getNotificationsFixture } from "@/lib/demo-data/runtime-data";
import { runKeys } from "@/lib/query-keys";

export function useRunNotifications(runId: string) {
  return useQuery({
    queryKey: runKeys.notifications(runId),
    queryFn: async () => {
      await new Promise((resolve) => setTimeout(resolve, 40));
      return getNotificationsFixture(runId);
    },
  });
}
