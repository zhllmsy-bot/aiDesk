import type { EvidenceRef, ExecutorAttempt, MemoryHit } from "@ai-desk/contracts-execution";

const evidence: EvidenceRef[] = [
  {
    id: "evidence_patch_diff",
    type: "artifact",
    label: "Patch diff",
    href: "/artifacts/artifact_patch_001",
  },
];

const memoryHits: MemoryHit[] = [
  {
    id: "mem_runtime_guardrail",
    namespace: "runtime",
    summary: "Protected workflow files require approval before write execution resumes.",
    score: 0.91,
    retentionPolicy: "retain_for_project",
    recallCount: 3,
    version: 1,
  },
];

const attempts: ExecutorAttempt[] = [
  {
    id: "att_patch_002",
    schemaVersion: "2026-04-19.execution.v1",
    executor: "codex-executor",
    summary: "Patch generated and paused on guarded workflow approval.",
    startedAt: "2026-04-19T00:39:20Z",
    finishedAt: "2026-04-19T00:43:05Z",
    correlation: {
      projectId: "proj_meridian",
      runId: "run_20260419_main",
      taskId: "task_patch_guard",
      attemptId: "att_patch_002",
    },
    evidenceRefs: evidence,
    memoryHits,
    verification: {
      verdict: "warning",
      summary: "Verification passed syntax checks but requires approval.",
      checks: [],
    },
    security: {
      scope: "write_execution",
      approvalRequired: true,
      writeAllowed: false,
      usedSecret: false,
    },
  },
];

export function getEvidenceFixture(_attemptId: string) {
  return evidence;
}

export function getMemoryHitsFixture(_attemptId: string) {
  return memoryHits;
}

export function getExecutorAttemptFixture(attemptId: string) {
  return attempts.find((attempt) => attempt.id === attemptId) ?? null;
}
