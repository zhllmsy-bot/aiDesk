import type { ProjectRole, WorkspaceSession } from "@ai-desk/contracts-projects";

export function createWorkspaceSession(input: {
  display_name: string;
  email: string;
  role: ProjectRole;
  active_project_id?: string | null;
}): WorkspaceSession {
  return {
    schema_version: "2026-04-19.1",
    user_id: input.email,
    display_name: input.display_name,
    email: input.email,
    roles: [input.role],
    active_project_id: input.active_project_id ?? null,
    is_authenticated: true,
  };
}
