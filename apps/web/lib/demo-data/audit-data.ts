export type AuditStageKey = "survey" | "counter_argument" | "roadmap";

export type AuditStage = {
  key: AuditStageKey;
  title: string;
  status: "complete" | "needs_review" | "planned";
  summary: string;
  findings: string[];
  citations: Array<{
    label: string;
    href: string;
  }>;
};

export type AuditCanvasRecord = {
  projectId: string;
  projectName: string;
  auditMode: "three_pass";
  runId: string;
  generatedAt: string;
  confidence: "high" | "medium" | "low";
  thesis: string;
  diffSummary: string[];
  stages: AuditStage[];
};

const auditCanvases: AuditCanvasRecord[] = [
  {
    projectId: "proj_meridian",
    projectName: "Meridian Control Plane",
    auditMode: "three_pass",
    runId: "run_20260419_main",
    generatedAt: "2026-04-19T00:47:00Z",
    confidence: "high",
    thesis:
      "Temporal durability and guarded execution are strong enough for a self-hosted beta, while UI governance and onboarding now define the release risk.",
    diffSummary: [
      "Kernel, integrations, and contract boundaries are present and checked by workspace scripts.",
      "Operator approval remains the control point for protected workflow writes.",
      "First-run proof still depends on demo project and audit-specific presentation.",
    ],
    stages: [
      {
        key: "survey",
        title: "Survey",
        status: "complete",
        summary:
          "The runtime lane exposes workflow events, task graph state, approval requests, and notification evidence from one correlated run.",
        findings: [
          "Control plane and runtime contracts have source ownership instead of snapshot-only artifacts.",
          "LangGraph persistence has been lifted into kernel-level code.",
          "Memory adapters and LLM providers now sit below explicit integration boundaries.",
        ],
        citations: [
          { label: "Runtime timeline", href: "/runs/run_20260419_main/timeline" },
          { label: "Trace telemetry", href: "/runs/run_20260419_main/telemetry" },
        ],
      },
      {
        key: "counter_argument",
        title: "Counter Argument",
        status: "needs_review",
        summary:
          "The strongest objection is not core durability; it is whether a new operator can reach the first useful audit without understanding the whole stack.",
        findings: [
          "Quickstart needs a visible demo path before external contributors arrive.",
          "UI primitives must stay enforced at CI level to prevent hand-rolled workflow screens.",
          "Worker deployment should be separate from API ownership even if code still shares the API package.",
        ],
        citations: [
          { label: "Project run", href: "/projects/proj_meridian/runs/run_20260419_main" },
          { label: "Decision queue", href: "/review" },
        ],
      },
      {
        key: "roadmap",
        title: "Roadmap",
        status: "planned",
        summary:
          "The next product slice should turn this canvas into the default audit destination after importing a repository.",
        findings: [
          "Promote the demo project into the quickstart path.",
          "Add OpenTelemetry export and policy bundle validation as release gates.",
          "Split worker process packaging first, then move worker source ownership when API contracts settle.",
        ],
        citations: [
          { label: "Worker task", href: "/runs/run_20260419_main/tasks/task_patch_guard" },
          { label: "Evidence path", href: "/artifacts" },
        ],
      },
    ],
  },
];

export function getAuditCanvas(projectId: string) {
  const fallback = auditCanvases[0];
  if (!fallback) {
    throw new Error("Audit canvas fixtures are not configured");
  }
  return auditCanvases.find((canvas) => canvas.projectId === projectId) ?? fallback;
}
