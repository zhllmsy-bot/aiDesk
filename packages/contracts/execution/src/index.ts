import type { ApiSchemas } from "@ai-desk/contracts-api";

export const executionSchemaVersion = "2026-04-19.execution.v1" as const;

export type ApprovalSummary = ApiSchemas["ApprovalSummaryView"];
export type ApprovalDetail = ApiSchemas["ApprovalDetailView"];
export type EvidenceRef = ApiSchemas["EvidenceRefView"];
export type MemoryHit = ApiSchemas["MemoryHitView"];
export type ExecutorAttempt = ApiSchemas["ExecutorAttemptView"];

export interface ArtifactRecord {
  id: string;
  name: string;
  type: string;
  href: string;
  runId?: string | null;
  taskId?: string | null;
  attemptId?: string | null;
  summary?: string | null;
  createdAt: string;
  metadata?: Record<string, unknown>;
}

export interface ArtifactListResponse {
  items: ArtifactRecord[];
}
