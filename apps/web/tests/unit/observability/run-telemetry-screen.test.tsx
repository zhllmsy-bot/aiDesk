import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type React from "react";
import { describe, expect, it } from "vitest";

import { RunTelemetryScreen } from "@/features/observability/components/run-telemetry-screen";

function renderWithQuery(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("run telemetry screen", () => {
  it("renders spans, worker health, and notification delivery", async () => {
    renderWithQuery(<RunTelemetryScreen runId="run_20260419_main" />);

    expect(await screen.findByText("Trace trace_patch_guard")).toBeInTheDocument();
    expect(screen.getByText("Recovery and delivery window")).toBeInTheDocument();
    expect(screen.getByText("Notification failure rate")).toBeInTheDocument();
    expect(screen.getByText("Correlated spans")).toBeInTheDocument();
    expect(screen.getByText("worker-runtime-a")).toBeInTheDocument();
    expect(screen.getByText("Approval required for guarded workflow patch.")).toBeInTheDocument();
  });
});
