import Link from "next/link";

import type { WorkspaceProjectListItem } from "@ai-desk/contracts-projects";
import { Button, StatusBadge } from "@ai-desk/ui";

import { projectRoutes } from "../routes";

export function ProjectsTable({ items }: { items: WorkspaceProjectListItem[] }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Branch</th>
            <th>Role</th>
            <th>Updated</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <strong>{item.name}</strong>
                <div className="graph-task-id">{item.root_path}</div>
              </td>
              <td>
                <StatusBadge
                  label={item.status}
                  tone={item.status === "needs_attention" ? "warning" : "neutral"}
                />
              </td>
              <td>{item.default_branch}</td>
              <td>{item.current_user_role ?? "viewer"}</td>
              <td>{item.updated_at}</td>
              <td>
                <div className="inline-actions">
                  <Link href={projectRoutes.audit({ projectId: item.id })}>
                    <Button>Audit</Button>
                  </Link>
                  <Link href={projectRoutes.detail({ projectId: item.id })}>
                    <Button tone="secondary">Open</Button>
                  </Link>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
