import type { ArtifactRecord } from "@ai-desk/contracts-execution";

const artifacts: ArtifactRecord[] = [
  {
    id: "artifact_patch_001",
    name: "Guarded patch diff",
    type: "patch",
    href: "/artifacts/artifact_patch_001",
    runId: "run_20260419_main",
    taskId: "task_patch_guard",
    attemptId: "att_patch_002",
    summary: "Patch artifact linked before guarded workflow approval.",
    createdAt: "2026-04-19T00:42:00Z",
  },
];

export function listArtifactFixtures() {
  return artifacts;
}

export function getArtifactFixture(artifactId: string) {
  return artifacts.find((artifact) => artifact.id === artifactId) ?? null;
}
