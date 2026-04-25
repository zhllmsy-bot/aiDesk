import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RunOverviewScreen } from "@/features/runs/components/run-overview-screen";

vi.mock("next/navigation", () => ({
  usePathname: () => "/runs/run_20260419_main/timeline",
  useRouter: () => ({
    replace: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

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

describe("run overview screen", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/runs/run_20260419_main/timeline");
  });

  it("renders workflow status, timeline, and graph entry points", async () => {
    renderWithQuery(<RunOverviewScreen runId="run_20260419_main" />);

    expect(
      await screen.findByText("Meridian Control Plane / run_20260419_main"),
    ).toBeInTheDocument();
    expect(screen.getByText("Runtime history")).toBeInTheDocument();
    expect(await screen.findByText("Subagent execution plan")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Telemetry" })).toBeInTheDocument();
  });
});
