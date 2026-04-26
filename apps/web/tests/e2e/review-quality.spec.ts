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

test("@a11y decision queue has no serious accessibility regressions", async ({ page }) => {
  await page.goto("/review");
  await expect(page.getByRole("heading", { name: "Decision queue" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open detail" }).first()).toBeVisible();

  const accessibility = await new AxeBuilder({ page }).analyze();
  const seriousViolations = accessibility.violations.filter((violation) =>
    ["critical", "serious"].includes(violation.impact ?? ""),
  );
  expect(seriousViolations).toEqual([]);
});

test("@visual decision queue matches the approved baseline", async ({ page }) => {
  await page.goto("/review");
  await expect(page.getByRole("heading", { name: "Decision queue" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open detail" }).first()).toBeVisible();
  await expect(page).toHaveScreenshot("decision-queue.png", {
    maxDiffPixelRatio: 0.001,
  });
});
