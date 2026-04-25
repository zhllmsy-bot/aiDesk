import type { ApiSchemas } from "@ai-desk/contracts-api";
import type {
  CreateWorkspaceProjectInput,
  UpdateWorkspaceProjectInput,
  WorkspaceIterationPageResponse,
  WorkspaceProjectDetailResponse,
  WorkspaceProjectListItem,
  WorkspaceProjectListQuery,
  WorkspaceProjectListResponse,
} from "@ai-desk/contracts-projects";

import { getServerApiClient } from "@/lib/server-api-client";

const schemaVersion = "2026-04-19.1" as const;

type ProjectListItemModel = ApiSchemas["ProjectListItemModel"];
type ProjectDetailResponse = ApiSchemas["ProjectDetailResponse"];
type IterationListResponse = ApiSchemas["IterationListResponse"];
type PlanSummaryResponse = ApiSchemas["PlanSummaryResponse"];
type ProjectStatus = WorkspaceProjectListItem["status"];

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

function statusFromBackend(status: ApiSchemas["ProjectStatus"]): ProjectStatus {
  return status === "archived" ? "archived" : "active";
}

function buildMemberships(
  projectId: string,
  role: ApiSchemas["ProjectRole"] | null,
  grantedAt: string,
) {
  if (!role) {
    return [];
  }

  return [
    {
      project_id: projectId,
      role,
      granted_at: grantedAt,
    },
  ];
}

function baseProjectFields(item: ProjectListItemModel | ProjectDetailResponse) {
  const memberships = buildMemberships(item.id, item.current_user_role, item.updated_at);
  return {
    id: item.id,
    name: item.name,
    slug: item.slug,
    root_path: item.root_path,
    default_branch: item.default_branch,
    description: item.description,
    status: statusFromBackend(item.status),
    repo_name: item.root_path.split("/").filter(Boolean).at(-1) ?? item.slug,
    repo_provider: "local" as const,
    last_synced_at: item.updated_at,
    current_user_role: item.current_user_role,
    memberships,
    latest_iteration: null,
    latest_plan: null,
    latest_run: null,
    created_at: item.created_at,
    updated_at: item.updated_at,
  };
}

function mapPlanSummary(planSummary: PlanSummaryResponse["latest_plan"]) {
  if (!planSummary) {
    return null;
  }

  return {
    id: planSummary.id,
    goal: planSummary.title,
    scope: [],
    constraints: [],
    status: planSummary.status,
    created_at: planSummary.created_at,
    updated_at: planSummary.updated_at,
  };
}

function mapIteration(
  iteration: IterationListResponse["items"][number],
  latestPlan: ReturnType<typeof mapPlanSummary>,
) {
  return {
    id: iteration.id,
    iteration_no: iteration.sequence_number,
    summary: iteration.title,
    status: iteration.status,
    created_at: iteration.created_at,
    updated_at: iteration.updated_at,
    latest_plan: latestPlan,
    latest_run: null,
  };
}

function applyListFilters(
  items: WorkspaceProjectListItem[],
  query: Required<WorkspaceProjectListQuery>,
) {
  const normalizedSearch = query.search.trim().toLowerCase();

  return items
    .filter((item) => query.status === "all" || item.status === query.status)
    .filter((item) => {
      if (!normalizedSearch) {
        return true;
      }

      return [item.name, item.description ?? "", item.root_path, item.repo_name]
        .join(" ")
        .toLowerCase()
        .includes(normalizedSearch);
    });
}

function sortQueryToBackend(sort: Required<WorkspaceProjectListQuery>["sort"]) {
  switch (sort) {
    case "name_asc":
      return { sort_by: "name" as const, sort_order: "asc" as const };
    case "name_desc":
      return { sort_by: "name" as const, sort_order: "desc" as const };
    case "updated_at_asc":
      return { sort_by: "updated_at" as const, sort_order: "asc" as const };
    default:
      return { sort_by: "updated_at" as const, sort_order: "desc" as const };
  }
}

async function getProjectReadModel(projectId: string) {
  const serverApi = await getServerApiClient();
  if (!serverApi) {
    return null;
  }

  const projectResult = await serverApi.client.GET("/projects/{project_id}", {
    params: { path: { project_id: projectId } },
  });
  if (!projectResult.data) {
    return null;
  }

  const [iterationsResult, planSummaryResult] = await Promise.all([
    serverApi.client.GET("/projects/{project_id}/iterations", {
      params: { path: { project_id: projectId } },
    }),
    serverApi.client.GET("/projects/{project_id}/plan-summary", {
      params: { path: { project_id: projectId } },
    }),
  ]);

  if (!iterationsResult.data || !planSummaryResult.data) {
    return null;
  }

  const latestPlan = mapPlanSummary(planSummaryResult.data.latest_plan);
  const iterations = [...iterationsResult.data.items]
    .sort((left, right) => right.sequence_number - left.sequence_number)
    .map((iteration) =>
      mapIteration(
        iteration,
        latestPlan && planSummaryResult.data.latest_plan?.iteration_id === iteration.id
          ? latestPlan
          : null,
      ),
    );

  const project = {
    ...baseProjectFields(projectResult.data),
    latest_iteration: iterations[0] ?? null,
    latest_plan: latestPlan,
  };

  return {
    schema_version: schemaVersion,
    item: {
      project,
      summary: {
        active_run_count: 0,
        waiting_approval_count: 0,
        open_artifact_count: 0,
      },
      iterations,
      recent_runs: [],
      current_membership: project.memberships[0] ?? null,
    },
  } satisfies WorkspaceProjectDetailResponse;
}

export async function listProjectsViaControlPlane(
  query: WorkspaceProjectListQuery,
): Promise<WorkspaceProjectListResponse | null> {
  const serverApi = await getServerApiClient();
  if (!serverApi) {
    return null;
  }

  const normalizedQuery = normalizeQuery(query);
  const sort = sortQueryToBackend(normalizedQuery.sort);

  const result = await serverApi.client.GET("/projects", {
    params: {
      query: {
        page: 1,
        page_size: 100,
        sort_by: sort.sort_by,
        sort_order: sort.sort_order,
        status:
          normalizedQuery.status === "all" || normalizedQuery.status === "needs_attention"
            ? undefined
            : normalizedQuery.status,
      },
    },
  });

  if (!result.data) {
    return null;
  }

  const items = applyListFilters(
    result.data.items.map((item) => baseProjectFields(item)),
    normalizedQuery,
  );

  return {
    schema_version: schemaVersion,
    query: normalizedQuery,
    items,
  };
}

export async function getProjectDetailViaControlPlane(
  projectId: string,
): Promise<WorkspaceProjectDetailResponse | null> {
  return getProjectReadModel(projectId);
}

export async function importProjectViaControlPlane(
  input: CreateWorkspaceProjectInput,
): Promise<WorkspaceProjectDetailResponse | null> {
  const serverApi = await getServerApiClient();
  if (!serverApi) {
    return null;
  }

  const createResult = await serverApi.client.POST("/projects", {
    body: {
      name: input.name,
      root_path: input.root_path,
      default_branch: input.default_branch,
      description: input.description ?? null,
    },
  });

  if (!createResult.data) {
    return null;
  }

  return getProjectReadModel(createResult.data.id);
}

export async function updateProjectViaControlPlane(
  projectId: string,
  input: UpdateWorkspaceProjectInput,
): Promise<WorkspaceProjectDetailResponse | null> {
  const serverApi = await getServerApiClient();
  if (!serverApi) {
    return null;
  }

  const updateResult = await serverApi.client.PATCH("/projects/{project_id}", {
    params: {
      path: {
        project_id: projectId,
      },
    },
    body: {
      name: input.name,
      default_branch: input.default_branch,
      description: input.description ?? null,
    },
  });

  if (!updateResult.data) {
    return null;
  }

  return getProjectReadModel(projectId);
}

export async function archiveProjectViaControlPlane(
  projectId: string,
): Promise<WorkspaceProjectDetailResponse | null> {
  const serverApi = await getServerApiClient();
  if (!serverApi) {
    return null;
  }

  const archiveResult = await serverApi.client.POST("/projects/{project_id}/archive", {
    params: {
      path: {
        project_id: projectId,
      },
    },
  });

  if (!archiveResult.data) {
    return null;
  }

  return getProjectReadModel(projectId);
}

export async function getIterationPageViaControlPlane(
  projectId: string,
  iterationId: string,
): Promise<WorkspaceIterationPageResponse | null> {
  const detail = await getProjectReadModel(projectId);
  if (!detail) {
    return null;
  }

  const iteration = detail.item.iterations.find((item) => item.id === iterationId);
  if (!iteration) {
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
      related_runs: [],
    },
  };
}
