"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useDeferredValue } from "react";

import { Button, Input, Panel, Select, StatusBadge } from "@ai-desk/ui";

import type {
  WorkspaceProjectListQuery,
  WorkspaceProjectStatus,
} from "@ai-desk/contracts-projects";

import { useProjectsList } from "../hooks/use-projects-list";
import { ProjectImportForm } from "./project-import-form";
import { ProjectsCards } from "./projects-cards";
import { ProjectsEmptyState } from "./projects-empty-state";
import { ProjectsTable } from "./projects-table";

function readQuery(searchParams: URLSearchParams): Required<WorkspaceProjectListQuery> {
  return {
    search: searchParams.get("search") ?? "",
    status: (searchParams.get("status") as WorkspaceProjectStatus | "all" | null) ?? "all",
    sort:
      (searchParams.get("sort") as Required<WorkspaceProjectListQuery>["sort"] | null) ??
      "updated_at_desc",
    view:
      (searchParams.get("view") as Required<WorkspaceProjectListQuery>["view"] | null) ?? "table",
  };
}

export function ProjectsIndexScreen() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = readQuery(searchParams);
  const deferredSearch = useDeferredValue(query.search);
  const { data, isLoading, isError, refetch } = useProjectsList({
    ...query,
    search: deferredSearch,
  });

  const updateQuery = (patch: Partial<Required<WorkspaceProjectListQuery>>) => {
    const next = new URLSearchParams(searchParams.toString());

    for (const [key, value] of Object.entries({ ...query, ...patch })) {
      if (!value || value === "all" || (value === "table" && key === "view")) {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }

    const suffix = next.toString();
    router.replace(suffix ? `${pathname}?${suffix}` : pathname);
  };

  const items = data?.items ?? [];

  return (
    <div className="page-stack">
      <Panel
        eyebrow="Control"
        title="Autonomous project queue"
        actions={
          isLoading ? (
            <StatusBadge label="loading" tone="info" />
          ) : (
            <StatusBadge label={`${items.length} visible`} tone="neutral" />
          )
        }
      >
        <div className="hero-grid">
          <div className="hero-copy">
            <p className="ui-copy">
              Projects under autonomous control, active runs, and operator attention are grouped
              into one operational queue.
            </p>

            <div className="toolbar-grid">
              <Input
                aria-label="Search projects"
                value={query.search}
                onChange={(event) => updateQuery({ search: event.target.value })}
                placeholder="Search by name, root path, or repo"
              />
              <Select
                aria-label="Status filter"
                value={query.status}
                onChange={(event) =>
                  updateQuery({
                    status: event.target.value as Required<WorkspaceProjectListQuery>["status"],
                  })
                }
              >
                <option value="all">All statuses</option>
                <option value="active">Active</option>
                <option value="needs_attention">Needs attention</option>
                <option value="archived">Archived</option>
              </Select>
              <Select
                aria-label="Sort projects"
                value={query.sort}
                onChange={(event) =>
                  updateQuery({
                    sort: event.target.value as Required<WorkspaceProjectListQuery>["sort"],
                  })
                }
              >
                <option value="updated_at_desc">Recently updated</option>
                <option value="updated_at_asc">Oldest updated</option>
                <option value="name_asc">Name A-Z</option>
                <option value="name_desc">Name Z-A</option>
              </Select>
              <div className="inline-actions">
                <Button
                  tone={query.view === "table" ? "primary" : "secondary"}
                  onClick={() => updateQuery({ view: "table" })}
                >
                  Table
                </Button>
                <Button
                  tone={query.view === "cards" ? "primary" : "secondary"}
                  onClick={() => updateQuery({ view: "cards" })}
                >
                  Cards
                </Button>
              </div>
            </div>
          </div>

          <div className="hero-metrics">
            <div className="metric-card">
              <span className="ui-eyebrow">Visible</span>
              <strong>{items.length}</strong>
              <p className="ui-copy">Projects matching this command view.</p>
            </div>
            <div className="metric-card">
              <span className="ui-eyebrow">Running</span>
              <strong>
                {items.filter((item) => item.latest_run?.status === "running").length}
              </strong>
              <p className="ui-copy">Active autonomous workflows.</p>
            </div>
            <div className="metric-card">
              <span className="ui-eyebrow">Attention</span>
              <strong>
                {
                  items.filter(
                    (item) =>
                      item.status === "needs_attention" ||
                      item.latest_run?.status === "failed" ||
                      item.latest_run?.status === "paused" ||
                      item.latest_run?.status === "retrying",
                  ).length
                }
              </strong>
              <p className="ui-copy">Projects that should be inspected first.</p>
            </div>
            <div className="metric-card">
              <span className="ui-eyebrow">Active</span>
              <strong>{items.filter((item) => item.status === "active").length}</strong>
              <p className="ui-copy">Projects still allowed to self-iterate.</p>
            </div>
          </div>
        </div>
      </Panel>

      <Panel eyebrow={query.view === "cards" ? "Cards" : "Table"} title="Project status">
        {isError ? (
          <ProjectsEmptyState
            title="Could not load projects"
            description="The project index request failed. Retry to restore the current search state."
            action={{ label: "Retry", href: pathname }}
          />
        ) : isLoading ? (
          <div className="surface-note">Loading project index...</div>
        ) : items.length === 0 ? (
          <ProjectsEmptyState
            title="No projects match the current filters"
            description="Adjust the search or import a new project to populate the workspace."
          />
        ) : query.view === "cards" ? (
          <ProjectsCards items={items} />
        ) : (
          <ProjectsTable items={items} />
        )}

        {isError ? (
          <div className="inline-actions">
            <Button tone="secondary" onClick={() => refetch()}>
              Retry request
            </Button>
          </div>
        ) : null}
      </Panel>

      <ProjectImportForm />
    </div>
  );
}
