import AxeBuilder from "@axe-core/playwright";
import { type Page, expect, test } from "@playwright/test";

const workspaceSession = {
  schema_version: "2026-04-19.1",
  user_id: "user_admin",
  display_name: "Admin Operator",
  email: "admin@example.com",
  roles: ["admin"],
  active_project_id: "proj_atlas",
  is_authenticated: true,
};

const surfaceCases = [
  {
    heading: "Enter the AI run control room",
    route: "/login",
    slug: "login",
    authenticated: false,
  },
  {
    heading: "Autonomous project queue",
    route: "/projects",
    slug: "workspace-shell",
  },
  {
    heading: "Operator decisions with provenance",
    route: "/review",
    slug: "approval-center",
  },
  {
    heading: "Meridian Control Plane audit canvas",
    route: "/projects/proj_meridian/audit",
    slug: "audit-canvas",
  },
  {
    heading: "Open a run command surface",
    route: "/runs",
    slug: "runs-index",
  },
  {
    heading: "Meridian Control Plane / run_20260419_main",
    route: "/runs/run_20260419_main/timeline",
    slug: "run-overview",
  },
] as const;

type SurfaceCase = (typeof surfaceCases)[number];
type Theme = "dawn" | "midnight";

test.use({
  viewport: {
    width: 1440,
    height: 1100,
  },
});

async function applyBootState(page: Page, options: { authenticated?: boolean; theme: Theme }) {
  await page.addInitScript(
    ({ session, theme, authenticated }) => {
      window.localStorage.setItem("ai-desk.theme", theme);
      document.documentElement.dataset.theme = theme;
      const applyBodyTheme = () => {
        if (document.body) {
          document.body.dataset.theme = theme;
        }
      };
      if (document.body) {
        applyBodyTheme();
      } else {
        document.addEventListener("DOMContentLoaded", applyBodyTheme, { once: true });
      }
      if (authenticated) {
        window.sessionStorage.setItem("ai-desk.workspace-session", JSON.stringify(session));
      } else {
        window.sessionStorage.removeItem("ai-desk.workspace-session");
      }
    },
    {
      authenticated: options.authenticated ?? true,
      session: workspaceSession,
      theme: options.theme,
    },
  );
}

async function openSurface(page: Page, surface: SurfaceCase, theme: Theme) {
  await applyBootState(page, { authenticated: surface.authenticated, theme });
  await page.goto(surface.route);
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: surface.heading }).first()).toBeVisible();
}

for (const surface of surfaceCases) {
  test(`@a11y ${surface.slug} has no serious accessibility regressions`, async ({ page }) => {
    await openSurface(page, surface, "midnight");

    const accessibility = await new AxeBuilder({ page }).analyze();
    const seriousViolations = accessibility.violations.filter((violation) =>
      ["critical", "serious"].includes(violation.impact ?? ""),
    );

    expect(seriousViolations).toEqual([]);
  });

  for (const theme of ["midnight", "dawn"] as const) {
    test(`@visual ${surface.slug} ${theme} matches the approved baseline`, async ({ page }) => {
      await openSurface(page, surface, theme);
      await expect(page).toHaveScreenshot(`${surface.slug}-${theme}.png`, {
        maxDiffPixelRatio: 0.001,
      });
    });
  }
}
