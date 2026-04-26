import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AuditCanvasScreen } from "@/features/projects/components/audit-canvas-screen";

describe("audit canvas screen", () => {
  it("renders the three-pass audit report with citations", () => {
    render(<AuditCanvasScreen projectId="proj_meridian" />);

    expect(
      screen.getByRole("heading", { name: "Meridian Control Plane audit canvas" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Survey")).toBeInTheDocument();
    expect(screen.getByText("Counter Argument")).toBeInTheDocument();
    expect(screen.getByText("Roadmap")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Runtime proof/ })).toHaveAttribute(
      "href",
      "/runs/run_20260419_main/timeline",
    );
  });
});
