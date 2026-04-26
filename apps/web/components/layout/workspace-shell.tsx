"use client";

import { usePathname } from "next/navigation";

import {
  Avatar,
  AvatarFallback,
  Breadcrumb,
  BreadcrumbCurrent,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
  Button,
  InlineActions,
  PageLayout,
  Sidebar,
  SidebarFooter,
  SidebarHeader,
  SidebarItem,
  SidebarNav,
  StatusBadge,
  SurfaceNote,
} from "@ai-desk/ui";

import { useAccessSession } from "@/features/access/access-context";
import { useProjectRegistry } from "@/features/projects/project-registry-context";

import { workspaceNavItems } from "./nav-config";
import { ThemeToggle } from "./theme-toggle";

const segmentLabels = {
  audit: "Audit",
  iterations: "Iterations",
  projects: "Projects",
  review: "Review",
  runs: "Runs",
  settings: "Settings",
};

const titleLabels = {
  artifacts: "Evidence",
  attempts: "Attempt ledger",
  audit: "Audit canvas",
  control: "Control room",
  review: "Decision queue",
  runs: "Runs",
  runCommand: "Run command",
};

const subtitleLabels = {
  artifacts: "Inspect generated outputs and the provenance chain behind each run.",
  attempts: "Read executor attempts, retries, memory hits, and verification evidence.",
  audit: "Compare survey, counter-argument, roadmap, citations, and deltas for one project audit.",
  control: "Monitor autonomous projects by current state, latest run, and next operator action.",
  review: "Approve, reject, or inspect only the decisions that can change an autonomous run.",
  runs: "Track what is executing now, what each subagent promised to do, and which event proves it.",
};

function breadcrumbLabel(
  segment: string,
  registry: Array<{ id: string; name: string }>,
  segmentLabels: Record<string, string>,
) {
  const project = registry.find((item) => item.id === segment);
  if (project) {
    return project.name;
  }

  if (segmentLabels[segment]) {
    return segmentLabels[segment];
  }

  return segment.replace(/[-_]/g, " ");
}

function workspaceTitle(
  segments: string[],
  registry: Array<{ id: string; name: string }>,
  labels: Record<string, string>,
  segmentLabels: Record<string, string>,
) {
  if (segments[0] === "runs") {
    return segments.length > 1 ? labels.runCommand : labels.runs;
  }

  if (segments[0] === "review") {
    return labels.review;
  }

  if (segments[0] === "artifacts") {
    return labels.artifacts;
  }

  if (segments[0] === "ops") {
    return labels.attempts;
  }

  if (segments[0] === "projects" && segments.length > 1) {
    if (segments.includes("audit")) {
      return labels.audit;
    }
    return breadcrumbLabel(segments[1] ?? "", registry, segmentLabels);
  }

  return labels.control;
}

function workspaceSubtitle(segments: string[], labels: Record<string, string>) {
  if (segments[0] === "runs") {
    return labels.runs;
  }

  if (segments[0] === "review") {
    return labels.review;
  }

  if (segments[0] === "artifacts") {
    return labels.artifacts;
  }

  if (segments[0] === "ops") {
    return labels.attempts;
  }

  if (segments[0] === "projects" && segments.includes("audit")) {
    return labels.audit;
  }

  return labels.control;
}

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const projectRegistry = useProjectRegistry();
  const { session, signOut } = useAccessSession();

  const segments = pathname.split("/").filter(Boolean);
  const displayName = session?.display_name ?? "Guest";
  const displayInitial = displayName.slice(0, 1).toUpperCase();

  return (
    <div className="workspace-shell">
      <Sidebar>
        <SidebarHeader>
          <div aria-hidden="true" className="ui-sidebar-brand-mark" />
          <div className="ui-eyebrow">AI Run Control</div>
          <h1 className="ui-sidebar-title">ai-desk</h1>
          <p className="ui-copy">Autonomous projects, observable subagents, operator control.</p>
        </SidebarHeader>

        <SidebarNav aria-label="Primary">
          {workspaceNavItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <SidebarItem
                active={isActive}
                description={item.description}
                href={item.href}
                key={item.key}
                label={item.label}
              />
            );
          })}
        </SidebarNav>

        <SidebarFooter>
          <SurfaceNote className="ui-user-menu">
            <Avatar aria-hidden="true">
              <AvatarFallback>{displayInitial}</AvatarFallback>
            </Avatar>
            <div>
              <strong>{displayName}</strong>
              <span>{session?.email ?? "No active session"}</span>
            </div>
          </SurfaceNote>
          <Button variant="ghost" onClick={signOut}>
            Sign out
          </Button>
        </SidebarFooter>
      </Sidebar>

      <main className="workspace-main">
        <PageLayout width="wide">
          <header className="workspace-topbar">
            <div className="workspace-topbar-copy">
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem>
                    <BreadcrumbLink href="/projects">Workspace</BreadcrumbLink>
                  </BreadcrumbItem>
                  {segments.map((segment, index) => {
                    const href = `/${segments.slice(0, index + 1).join("/")}`;
                    const label = breadcrumbLabel(segment, projectRegistry, segmentLabels);
                    const isLast = index === segments.length - 1;

                    return (
                      <BreadcrumbItem key={href}>
                        <BreadcrumbSeparator />
                        {isLast ? (
                          <BreadcrumbCurrent>{label}</BreadcrumbCurrent>
                        ) : (
                          <BreadcrumbLink href={href}>{label}</BreadcrumbLink>
                        )}
                      </BreadcrumbItem>
                    );
                  })}
                </BreadcrumbList>
              </Breadcrumb>
              <h2>{workspaceTitle(segments, projectRegistry, titleLabels, segmentLabels)}</h2>
              <p className="ui-copy">{workspaceSubtitle(segments, subtitleLabels)}</p>
            </div>

            <InlineActions>
              <StatusBadge
                label={session?.roles[0] ?? "guest"}
                tone={session?.is_authenticated ? "info" : "warning"}
              />
              <ThemeToggle />
            </InlineActions>
          </header>

          {children}
        </PageLayout>
      </main>
    </div>
  );
}
