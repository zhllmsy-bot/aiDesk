import type {
  ArchiveWorkspaceProjectInput,
  CreateWorkspaceProjectInput,
  UpdateWorkspaceProjectInput,
  WorkspaceIterationPageResponse,
  WorkspaceIterationSummary,
  WorkspaceProjectDetailResponse,
  WorkspaceProjectListItem,
  WorkspaceProjectListQuery,
  WorkspaceProjectListResponse,
} from "@ai-desk/contracts-projects";

const schemaVersion = "2026-04-19.1" as const;
const now = "2026-04-25T00:00:00Z";

const iterations: WorkspaceIterationSummary[] = [
  {
    id: "iter_meridian_001",
    iteration_no: 1,
    summary: "Runtime durability and operator approval loop",
    status: "active",
    created_at: now,
    updated_at: now,
    latest_plan: {
      id: "plan_meridian_001",
      goal: "Close runtime execution loop",
      scope: ["runtime", "review", "observability"],
      constraints: ["least privilege", "durable audit"],
      status: "ready",
      created_at: now,
      updated_at: now,
    },
    latest_run: {
      id: "run_20260419_main",
      workflow_name: "task.execution",
      status: "waiting_approval",
      started_at: "2026-04-19T00:39:00Z",
      updated_at: "2026-04-19T00:47:00Z",
      current_task_title: "Patch runtime retry guardrail",
      waiting_for_approval: true,
    },
  },
];

const projects = new Map<string, WorkspaceProjectListItem>([
  [
    "proj_meridian",
    {
      id: "proj_meridian",
      name: "Meridian Control Plane",
      slug: "meridian-control-plane",
      root_path: "/Users/admin/Desktop/ai-desk",
      default_branch: "main",
      description: "Runtime, review, and telemetry control plane for autonomous project work.",
      status: "needs_attention",
      repo_name: "ai-desk",
      repo_provider: "local",
      last_synced_at: now,
      current_user_role: "admin",
      memberships: [{ project_id: "proj_meridian", role: "admin", granted_at: now }],
      latest_iteration: iterations[0] ?? null,
      latest_plan: iterations[0]?.latest_plan ?? null,
      latest_run: iterations[0]?.latest_run ?? null,
      created_at: "2026-04-19T00:00:00Z",
      updated_at: now,
    },
  ],
  [
    "proj_atlas",
    {
      id: "proj_atlas",
      name: "Atlas Control Plane",
      slug: "atlas-control-plane",
      root_path: "/Users/admin/Desktop/atlas",
      default_branch: "main",
      description: "Example local workspace used by development session bootstrap.",
      status: "active",
      repo_name: "atlas",
      repo_provider: "local",
      last_synced_at: now,
      current_user_role: "maintainer",
      memberships: [{ project_id: "proj_atlas", role: "maintainer", granted_at: now }],
      latest_iteration: null,
      latest_plan: null,
      latest_run: null,
      created_at: "2026-04-18T00:00:00Z",
      updated_at: now,
    },
  ],
]);

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function normalizeQuery(
  query: WorkspaceProjectListQuery = {},
): Required<WorkspaceProjectListQuery> {
  return {
    search: query.search ?? "",
    status: query.status ?? "all",
    sort: query.sort ?? "updated_at_desc",
    view: query.view ?? "table",
  };
}

export function listWorkspaceProjects(
  query: WorkspaceProjectListQuery = {},
): WorkspaceProjectListResponse {
  const normalized = normalizeQuery(query);
  const search = normalized.search.trim().toLowerCase();
  const items = [...projects.values()]
    .filter((item) => normalized.status === "all" || item.status === normalized.status)
    .filter((item) =>
      search
        ? [item.name, item.description ?? "", item.root_path, item.repo_name]
            .join(" ")
            .toLowerCase()
            .includes(search)
        : true,
    )
    .sort((left, right) => {
      if (normalized.sort === "name_asc") {
        return left.name.localeCompare(right.name);
      }
      if (normalized.sort === "name_desc") {
        return right.name.localeCompare(left.name);
      }
      if (normalized.sort === "updated_at_asc") {
        return left.updated_at.localeCompare(right.updated_at);
      }
      return right.updated_at.localeCompare(left.updated_at);
    });

  return { schema_version: schemaVersion, query: normalized, items };
}

export function getWorkspaceProjectDetailResponse(
  projectId: string,
): WorkspaceProjectDetailResponse | null {
  const project = projects.get(projectId);
  if (!project) {
    return null;
  }
  const projectIterations = project.id === "proj_meridian" ? iterations : [];
  return {
    schema_version: schemaVersion,
    item: {
      project,
      summary: {
        active_run_count: project.latest_run ? 1 : 0,
        waiting_approval_count: project.latest_run?.waiting_for_approval ? 1 : 0,
        open_artifact_count: project.latest_run ? 1 : 0,
      },
      iterations: projectIterations,
      recent_runs: project.latest_run ? [project.latest_run] : [],
      current_membership: project.memberships[0] ?? null,
    },
  };
}

export function createWorkspaceProject(input: CreateWorkspaceProjectInput) {
  const slug = slugify(input.name);
  const id = `proj_${slug.replaceAll("-", "_")}`;
  const item: WorkspaceProjectListItem = {
    id,
    name: input.name,
    slug,
    root_path: input.root_path,
    default_branch: input.default_branch,
    description: input.description ?? null,
    status: "active",
    repo_name: input.root_path.split("/").filter(Boolean).at(-1) ?? slug,
    repo_provider: "local",
    last_synced_at: now,
    current_user_role: "admin",
    memberships: [{ project_id: id, role: "admin", granted_at: now }],
    latest_iteration: null,
    latest_plan: null,
    latest_run: null,
    created_at: now,
    updated_at: now,
  };
  projects.set(id, item);
  return item;
}

export function updateWorkspaceProject(projectId: string, input: UpdateWorkspaceProjectInput) {
  const current = projects.get(projectId);
  if (!current) {
    return null;
  }
  const updated = {
    ...current,
    name: input.name,
    default_branch: input.default_branch,
    description: input.description ?? null,
    updated_at: now,
  };
  projects.set(projectId, updated);
  return updated;
}

export function archiveWorkspaceProject(projectId: string, input: ArchiveWorkspaceProjectInput) {
  const current = projects.get(projectId);
  if (!current || current.name !== input.confirm_name) {
    return null;
  }
  const updated = { ...current, status: "archived" as const, updated_at: now };
  projects.set(projectId, updated);
  return updated;
}

export function deleteWorkspaceProject(projectId: string, input: ArchiveWorkspaceProjectInput) {
  const current = projects.get(projectId);
  if (!current || current.name !== input.confirm_name) {
    return false;
  }
  return projects.delete(projectId);
}

export function getWorkspaceIterationPageResponse(
  projectId: string,
  iterationId: string,
): WorkspaceIterationPageResponse | null {
  const detail = getWorkspaceProjectDetailResponse(projectId);
  const iteration = detail?.item.iterations.find((item) => item.id === iterationId);
  if (!detail || !iteration) {
    return null;
  }
  return {
    schema_version: schemaVersion,
    item: {
      project: {
        id: detail.item.project.id,
        name: detail.item.project.name,
        root_path: detail.item.project.root_path,
        slug: detail.item.project.slug,
      },
      iteration,
      related_runs: detail.item.recent_runs,
    },
  };
}

export function getRunContextLabel(runId: string) {
  const match = [...projects.values()].find((item) => item.latest_run?.id === runId);
  return match ? `${match.name} / ${match.latest_run?.workflow_name}` : "Runtime context pending";
}
