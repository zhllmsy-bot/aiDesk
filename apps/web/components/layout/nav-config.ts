import type { ProjectRole } from "@ai-desk/contracts-projects";

export type NavItem = {
  key: string;
  label: string;
  href: string;
  description: string;
  requiredRole?: ProjectRole;
  isVisible?: boolean;
};

export const workspaceNavItems: NavItem[] = [
  {
    key: "projects",
    label: "Control",
    href: "/projects",
    description: "Projects under autonomous run control.",
  },
  {
    key: "runtime",
    label: "Runs",
    href: "/runs",
    description: "Live execution, task plans, and event history.",
  },
  {
    key: "review",
    label: "Decisions",
    href: "/review",
    description: "Approvals that need operator intent.",
  },
  {
    key: "artifacts",
    label: "Evidence",
    href: "/artifacts",
    description: "Outputs, snapshots, and provenance.",
  },
  {
    key: "ops",
    label: "Attempts",
    href: "/ops/attempts/att_patch_002",
    description: "Executor attempts and operational traces.",
  },
];
