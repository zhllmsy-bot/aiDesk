"use client";

import { useQuery } from "@tanstack/react-query";

import type {
  WorkspaceProjectListQuery,
  WorkspaceProjectListResponse,
} from "@ai-desk/contracts-projects";

import { webFetch } from "@/lib/api-client";

async function fetchProjects(
  query: Required<WorkspaceProjectListQuery>,
): Promise<WorkspaceProjectListResponse> {
  const params = new URLSearchParams();
  if (query.search) {
    params.set("search", query.search);
  }
  if (query.status && query.status !== "all") {
    params.set("status", query.status);
  }
  if (query.sort !== "updated_at_desc") {
    params.set("sort", query.sort);
  }
  if (query.view !== "table") {
    params.set("view", query.view);
  }

  const response = await webFetch(`/api/projects?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Could not load projects.");
  }
  return (await response.json()) as WorkspaceProjectListResponse;
}

export function useProjectsList(query: Required<WorkspaceProjectListQuery>) {
  return useQuery({
    queryKey: ["projects", query],
    queryFn: () => fetchProjects(query),
  });
}
