import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.sessionStorage.setItem(
      "ai-desk.workspace-session",
      JSON.stringify({
        schema_version: "2026-04-19.1",
        user_id: "user_admin",
        display_name: "Admin Operator",
        email: "admin@example.com",
        roles: ["admin"],
        active_project_id: "proj_atlas",
        is_authenticated: true,
      }),
    );
  });
});

test("runtime timeline, task detail, and telemetry deep links work", async ({ page }) => {
  await page.goto("/runs/run_20260419_main/timeline");

  await expect(page.getByText("Meridian Control Plane / run_20260419_main")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Runtime history" })).toBeVisible();

  await page.getByRole("button", { name: "Task Running" }).click();
  await page.getByRole("link", { name: "Project run" }).first().click();
  await expect(page.getByText("A project-scoped view of this autonomous run.")).toBeVisible();

  await page.goto("/runs/run_20260419_main/tasks/task_patch_guard");
  await expect(page.getByText("Attempt history")).toBeVisible();

  await page.goto("/runs/run_20260419_main/telemetry");
  await expect(page.getByText("Runtime Health")).toBeVisible();

  const accessibility = await new AxeBuilder({ page }).analyze();
  const seriousViolations = accessibility.violations.filter((violation) =>
    ["critical", "serious"].includes(violation.impact ?? ""),
  );
  expect(seriousViolations).toEqual([]);
  await expect(page).toHaveScreenshot("runtime-telemetry.png", {
    maxDiffPixelRatio: 0.001,
  });

  await page.goto("/projects/proj_meridian/audit");
  await expect(
    page.getByRole("heading", { name: "Meridian Control Plane audit canvas" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Counter Argument" })).toBeVisible();

  await page.goto("/artifacts");
  await expect(page.getByRole("heading", { name: "Artifact ledger" })).toBeVisible();

  await page.goto("/ops/attempts/att_patch_002");
  await expect(page.getByRole("heading", { name: "codex-executor" })).toBeVisible();
});
