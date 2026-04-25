"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import type {
  CreateWorkspaceProjectInput,
  WorkspaceProjectDetailResponse,
} from "@ai-desk/contracts-projects";

import { webFetch } from "@/lib/api-client";

async function importProject(input: CreateWorkspaceProjectInput) {
  const response = await webFetch("/api/projects/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { message?: string } | null;
    throw new Error(payload?.message ?? "Import failed.");
  }
  return (await response.json()) as WorkspaceProjectDetailResponse;
}

export function useImportProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: importProject,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}
