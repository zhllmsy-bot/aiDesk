"use client";

import { useQuery } from "@tanstack/react-query";

import { getApproval } from "../api/get-approval";

export function useApprovalDetail(approvalId: string) {
  return useQuery({
    queryKey: ["review", "approval", approvalId],
    queryFn: () => getApproval(approvalId),
  });
}
