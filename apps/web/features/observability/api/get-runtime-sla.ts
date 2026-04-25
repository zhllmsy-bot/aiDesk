import { apiFetch, getApiErrorMessage } from "@/lib/api-client";

export type RuntimeSlaQuery = {
  windowHours?: number;
  projectId?: string;
  iterationId?: string;
  bucketMinutes?: number;
};

export type RuntimeSlaPoint = {
  bucket_start: string;
  event_count: number;
  workflow_retrying_count: number;
  approval_resolved_count: number;
  retry_recovered_count: number;
  failure_recovered_count: number;
  notifications_total: number;
  notifications_failed: number;
};

export type RuntimeSlaSnapshot = {
  generated_at?: string;
  window_hours: number;
  scope: {
    project_id: string | null;
    iteration_id: string | null;
  };
  run_count: number;
  event_count: number;
  retry_recovery: {
    count: number;
    avg_seconds: number | null;
    p50_seconds: number | null;
    p95_seconds: number | null;
  };
  approval_resolution: {
    count: number;
    avg_seconds: number | null;
    p50_seconds: number | null;
    p95_seconds: number | null;
  };
  failure_recovery: {
    count: number;
    avg_seconds: number | null;
    p50_seconds: number | null;
    p95_seconds: number | null;
  };
  notifications: {
    total: number;
    delivered: number;
    failed: number;
    channels: string[];
  };
  trend: {
    bucket_minutes: number;
    points: RuntimeSlaPoint[];
  };
};

function _fallbackSnapshot(query: RuntimeSlaQuery): RuntimeSlaSnapshot {
  return {
    window_hours: query.windowHours ?? 24 * 7,
    scope: {
      project_id: query.projectId ?? null,
      iteration_id: query.iterationId ?? null,
    },
    run_count: 0,
    event_count: 0,
    retry_recovery: { count: 0, avg_seconds: null, p50_seconds: null, p95_seconds: null },
    approval_resolution: { count: 0, avg_seconds: null, p50_seconds: null, p95_seconds: null },
    failure_recovery: { count: 0, avg_seconds: null, p50_seconds: null, p95_seconds: null },
    notifications: { total: 0, delivered: 0, failed: 0, channels: [] },
    trend: { bucket_minutes: query.bucketMinutes ?? 60, points: [] },
  };
}

export async function getRuntimeSla(query: RuntimeSlaQuery = {}): Promise<RuntimeSlaSnapshot> {
  const params = new URLSearchParams();
  params.set("window_hours", String(query.windowHours ?? 24 * 7));
  params.set("bucket_minutes", String(query.bucketMinutes ?? 60));
  if (query.projectId) {
    params.set("project_id", query.projectId);
  }
  if (query.iterationId) {
    params.set("iteration_id", query.iterationId);
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  const url = `${baseUrl}/observability/runtime-sla?${params.toString()}`;

  try {
    const response = await apiFetch(url, {
      method: "GET",
      cache: "no-store",
    });
    if (!response.ok) {
      let payload: unknown = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      throw new Error(getApiErrorMessage(payload, response.status));
    }
    return (await response.json()) as RuntimeSlaSnapshot;
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 80));
    return _fallbackSnapshot(query);
  }
}
