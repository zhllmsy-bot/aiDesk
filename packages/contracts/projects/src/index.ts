import type { ApiSchemas } from "@ai-desk/contracts-api";

export const projectContractSchemaVersion = "2026-04-19.1" as const;

export type ProjectRole = ApiSchemas["ProjectRole"];
export type WorkspaceProjectStatus = ApiSchemas["ProjectStatus"] | "needs_attention";
export type WorkspaceProjectSort = "updated_at_desc" | "updated_at_asc" | "name_asc" | "name_desc";
export type WorkspaceProjectView = "table" | "cards";

export interface WorkspaceSession {
  schema_version: typeof projectContractSchemaVersion | string;
  user_id: string;
  display_name: string;
  email: string;
  roles: ProjectRole[];
  active_project_id: string | null;
  is_authenticated: boolean;
}

export interface WorkspaceMembership {
  project_id: string;
  role: ProjectRole;
  granted_at: string;
}

export interface WorkspacePlanSummary {
  id: string;
  goal: string;
  scope: string[];
  constraints: string[];
  status: ApiSchemas["PlanStatus"];
  created_at: string;
  updated_at: string;
}

export interface WorkspaceRunSummary {
  id: string;
  workflow_name: string;
  status: string;
  started_at: string;
  updated_at: string;
  current_task_title?: string | null;
  waiting_for_approval?: boolean;
}

export interface WorkspaceIterationSummary {
  id: string;
  iteration_no: number;
  summary: string;
  status: string;
  created_at: string;
  updated_at: string;
  latest_plan: WorkspacePlanSummary | null;
  latest_run: WorkspaceRunSummary | null;
}

export interface WorkspaceProjectListItem {
  id: string;
  name: string;
  slug: string;
  root_path: string;
  default_branch: string;
  description: string | null;
  status: WorkspaceProjectStatus;
  repo_name: string;
  repo_provider: "local" | "github" | "gitlab" | "unknown";
  last_synced_at: string | null;
  current_user_role: ProjectRole | null;
  memberships: WorkspaceMembership[];
  latest_iteration: WorkspaceIterationSummary | null;
  latest_plan: WorkspacePlanSummary | null;
  latest_run: WorkspaceRunSummary | null;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceProjectListQuery {
  search?: string;
  status?: WorkspaceProjectStatus | "all";
  sort?: WorkspaceProjectSort;
  view?: WorkspaceProjectView;
}

export interface WorkspaceProjectListResponse {
  schema_version: typeof projectContractSchemaVersion | string;
  query: Required<WorkspaceProjectListQuery>;
  items: WorkspaceProjectListItem[];
}

export interface WorkspaceProjectDetailResponse {
  schema_version: typeof projectContractSchemaVersion | string;
  item: {
    project: WorkspaceProjectListItem;
    summary: {
      active_run_count: number;
      waiting_approval_count: number;
      open_artifact_count: number;
    };
    iterations: WorkspaceIterationSummary[];
    recent_runs: WorkspaceRunSummary[];
    current_membership: WorkspaceMembership | null;
  };
}

export interface WorkspaceIterationPageResponse {
  schema_version: typeof projectContractSchemaVersion | string;
  item: {
    project: {
      id: string;
      name: string;
      root_path: string;
      slug: string;
    };
    iteration: WorkspaceIterationSummary;
    related_runs: WorkspaceRunSummary[];
  };
}

export interface CreateWorkspaceProjectInput {
  name: string;
  root_path: string;
  default_branch: string;
  description?: string | null;
}

export interface UpdateWorkspaceProjectInput {
  name: string;
  default_branch: string;
  description?: string | null;
}

export interface ArchiveWorkspaceProjectInput {
  confirm_name: string;
}
