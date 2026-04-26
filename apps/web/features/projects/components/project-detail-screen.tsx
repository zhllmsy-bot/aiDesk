import Link from "next/link";

import { Button, Panel, StatusBadge } from "@ai-desk/ui";

import { projectRoutes } from "../routes";
import { listWorkspaceProjects } from "../server/project-store";

export function ProjectDetailScreen({ projectId }: { projectId: string }) {
  const project = listWorkspaceProjects().items.find((item) => item.id === projectId);

  if (!project) {
    return <div className="empty-state">Project {projectId} is unavailable.</div>;
  }

  return (
    <div className="page-stack">
      <Panel
        eyebrow="Project"
        title={project.name}
        actions={<StatusBadge label={project.status} tone="info" />}
      >
        <div className="run-command-grid">
          <div className="run-command-main">
            <p className="run-lead">{project.description ?? project.root_path}</p>
            <div className="signal-strip">
              <div className="signal-cell">
                <span>Repo</span>
                <strong>{project.repo_provider}</strong>
              </div>
              <div className="signal-cell">
                <span>Branch</span>
                <strong>{project.default_branch}</strong>
              </div>
              <div className="signal-cell">
                <span>Role</span>
                <strong>{project.current_user_role ?? "viewer"}</strong>
              </div>
            </div>
          </div>
          <div className="run-command-todos">
            <div className="ui-eyebrow">Primary paths</div>
            <Link href={projectRoutes.audit({ projectId })}>
              <Button>Open audit canvas</Button>
            </Link>
            {project.latest_run ? (
              <Link href={projectRoutes.run({ projectId, runId: project.latest_run.id })}>
                <Button tone="secondary">Open latest run</Button>
              </Link>
            ) : null}
          </div>
        </div>
      </Panel>
    </div>
  );
}
