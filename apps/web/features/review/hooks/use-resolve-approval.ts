"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { resolveApproval } from "../api/resolve-approval";

export function useResolveApproval() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: resolveApproval,
    onSuccess: (approval) => {
      queryClient.setQueryData(["review", "approval", approval.id], approval);
      void queryClient.invalidateQueries({ queryKey: ["review", "approvals"] });
    },
  });
}
