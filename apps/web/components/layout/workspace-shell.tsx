"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button, StatusBadge } from "@ai-desk/ui";

import { useAccessSession } from "@/features/access/access-context";
import { useProjectRegistry } from "@/features/projects/project-registry-context";

import { workspaceNavItems } from "./nav-config";
import { ThemeToggle } from "./theme-toggle";

function breadcrumbLabel(segment: string, registry: Array<{ id: string; name: string }>) {
  const project = registry.find((item) => item.id === segment);
  if (project) {
    return project.name;
  }

  if (segment === "projects") {
    return "Projects";
  }

  if (segment === "iterations") {
    return "Iterations";
  }

  if (segment === "runs") {
    return "Runs";
  }

  if (segment === "review") {
    return "Review";
  }

  if (segment === "settings") {
    return "Settings";
  }

  return segment.replace(/[-_]/g, " ");
}

function workspaceTitle(segments: string[], registry: Array<{ id: string; name: string }>) {
  if (segments[0] === "runs") {
    return segments.length > 1 ? "Run command" : "Runs";
  }

  if (segments[0] === "review") {
    return "Decision queue";
  }

  if (segments[0] === "artifacts") {
    return "Evidence";
  }

  if (segments[0] === "ops") {
    return "Attempt ledger";
  }

  if (segments[0] === "projects" && segments.length > 1) {
    return breadcrumbLabel(segments[1] ?? "", registry);
  }

  return "Control room";
}

function workspaceSubtitle(segments: string[]) {
  if (segments[0] === "runs") {
    return "Track what is executing now, what each subagent promised to do, and which event proves it.";
  }

  if (segments[0] === "review") {
    return "Approve, reject, or inspect only the decisions that can change an autonomous run.";
  }

  if (segments[0] === "artifacts") {
    return "Inspect generated outputs and the provenance chain behind each run.";
  }

  if (segments[0] === "ops") {
    return "Read executor attempts, retries, memory hits, and verification evidence.";
  }

  return "Monitor autonomous projects by current state, latest run, and next operator action.";
}

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const projectRegistry = useProjectRegistry();
  const { session, signOut } = useAccessSession();

  const segments = pathname.split("/").filter(Boolean);

  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar">
        <div className="workspace-brand">
          <div className="workspace-brand-mark" />
          <div className="ui-eyebrow">AI Run Control</div>
          <h1>ai-desk</h1>
          <p className="ui-copy">Autonomous projects, observable subagents, operator control.</p>
        </div>

        <nav className="workspace-nav" aria-label="Primary">
          {workspaceNavItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={item.key}
                href={item.href}
                className={`workspace-nav-link${isActive ? " workspace-nav-link-active" : ""}`}
              >
                <span className="workspace-nav-title">{item.label}</span>
                <span className="workspace-nav-copy">{item.description}</span>
              </Link>
            );
          })}
        </nav>

        <div className="workspace-sidebar-footer">
          <div className="surface-note">
            <strong>{session?.display_name ?? "Guest"}</strong>
            <div>{session?.email ?? "No active session"}</div>
          </div>
          <Button tone="ghost" onClick={signOut}>
            Sign out
          </Button>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <div className="workspace-topbar-copy">
            <div className="workspace-breadcrumbs" aria-label="Breadcrumbs">
              <Link href="/projects">Workspace</Link>
              {segments.map((segment, index) => {
                const href = `/${segments.slice(0, index + 1).join("/")}`;
                return (
                  <span key={href} className="workspace-breadcrumb-item">
                    <span className="workspace-breadcrumb-separator">/</span>
                    <Link href={href}>{breadcrumbLabel(segment, projectRegistry)}</Link>
                  </span>
                );
              })}
            </div>
            <h2>{workspaceTitle(segments, projectRegistry)}</h2>
            <p className="ui-copy">{workspaceSubtitle(segments)}</p>
          </div>

          <div className="workspace-topbar-actions">
            <StatusBadge
              label={session?.roles[0] ?? "guest"}
              tone={session?.is_authenticated ? "info" : "warning"}
            />
            <ThemeToggle />
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}
