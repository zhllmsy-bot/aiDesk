import Link from "next/link";

import type { WorkspaceProjectListItem } from "@ai-desk/contracts-projects";
import { Button, StatusBadge } from "@ai-desk/ui";

import { projectRoutes } from "../routes";

export function ProjectsCards({ items }: { items: WorkspaceProjectListItem[] }) {
  return (
    <div className="list-grid">
      {items.map((item) => (
        <article key={item.id} className="list-card">
          <div className="list-card-header">
            <div>
              <div className="ui-eyebrow">{item.repo_provider}</div>
              <h3>{item.name}</h3>
            </div>
            <StatusBadge
              label={item.status}
              tone={item.status === "needs_attention" ? "warning" : "neutral"}
            />
          </div>
          <p className="ui-copy">{item.description ?? item.root_path}</p>
          <div className="meta-row">
            <span>{item.default_branch}</span>
            <span>{item.current_user_role ?? "no role"}</span>
            <span>{item.updated_at}</span>
          </div>
          <Link href={projectRoutes.detail({ projectId: item.id })}>
            <Button>Open project</Button>
          </Link>
        </article>
      ))}
    </div>
  );
}
