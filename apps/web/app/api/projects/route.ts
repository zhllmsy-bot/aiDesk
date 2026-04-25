import { NextResponse } from "next/server";

import { listProjectsViaControlPlane } from "@/features/projects/server/control-plane-proxy";
import { listWorkspaceProjects } from "@/features/projects/server/project-store";

export async function GET(request: Request) {
  const query = {
    search: new URL(request.url).searchParams.get("search") ?? "",
    status:
      (new URL(request.url).searchParams.get("status") as
        | "active"
        | "archived"
        | "needs_attention"
        | "all"
        | null) ?? "all",
    sort:
      (new URL(request.url).searchParams.get("sort") as
        | "updated_at_desc"
        | "updated_at_asc"
        | "name_asc"
        | "name_desc"
        | null) ?? "updated_at_desc",
    view: (new URL(request.url).searchParams.get("view") as "table" | "cards" | null) ?? "table",
  };
  const backendResponse = await listProjectsViaControlPlane(query);
  if (backendResponse) {
    return NextResponse.json(backendResponse);
  }

  const { searchParams } = new URL(request.url);
  const response = listWorkspaceProjects({
    search: searchParams.get("search") ?? "",
    status:
      (searchParams.get("status") as "active" | "archived" | "needs_attention" | "all" | null) ??
      "all",
    sort:
      (searchParams.get("sort") as
        | "updated_at_desc"
        | "updated_at_asc"
        | "name_asc"
        | "name_desc"
        | null) ?? "updated_at_desc",
    view: (searchParams.get("view") as "table" | "cards" | null) ?? "table",
  });

  return NextResponse.json(response);
}
