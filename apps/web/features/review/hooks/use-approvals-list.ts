"use client";

import { useQuery } from "@tanstack/react-query";

import { listApprovals } from "../api/list-approvals";

export function useApprovalsList() {
  return useQuery({
    queryKey: ["review", "approvals"],
    queryFn: listApprovals,
  });
}
