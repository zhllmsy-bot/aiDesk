# 2026-04-26 Global Reassessment Completion TODO

Status: completed for the 2026-04-26 reassessment pass
Spec: `docs/specs/global-reassessment-architecture-governance.md`

This file converts the global reassessment into an auditable checklist. It intentionally separates current verified completion from the longer six-month roadmap in the spec.

## A. Spec And Planning Artifacts

- [x] Create a global architecture/governance spec grounded in the current repository state.
- [x] Classify the request as execution work, not a fresh conceptual audit.
- [x] Preserve the five structural epics: engineering governance, LLM/Agent abstraction, boundaries, UI hard constraints, policy/observability.
- [x] Record current repository evidence instead of repeating stale findings from older scans.
- [x] Add this completion TODO so the reassessment has a closed local artifact.
- [x] Link the new spec from `docs/specs/README.md`.

## B. Engineering Governance Baseline

- [x] Confirm root workspace exists through `pnpm-workspace.yaml`.
- [x] Confirm root TypeScript baseline exists through `tsconfig.base.json`.
- [x] Confirm root Biome config exists through `biome.json`.
- [x] Confirm GitHub Actions gates exist for CI, contracts, and e2e.
- [x] Add a PR template requiring validation commands, contract impact, UI primitive disclosure, and ADR/exemption links.
- [x] Confirm workspace package discovery lists API, web, UI, and all contract packages.

## C. Contracts And LLM/Agent Abstraction

- [x] Confirm contract packages exist for API, projects, runtime, execution, and LLM.
- [x] Confirm LLM contract source files exist for chat, tool, agent, and provider concepts.
- [x] Confirm Python LLM integration boundary exists under `api/integrations/llm`.
- [x] Confirm executor provider slots exist for OpenHands, Codex, Claude Code, Claude Agent, OpenAI Agents, Aider, and generic agent harness.
- [x] Confirm LLM SDK direct-import gate is wired through `scripts/check-import-boundaries.mjs`.

## D. Runtime And Migration Safety

- [x] Confirm Alembic versions are linearized with `0001` through `0006` naming.
- [x] Confirm pyright include covers workflows, runtime persistence, integrations, notifications, observability, and agent runtime.
- [x] Add request-side validation for oversized `workflow_run_id` values before persistence.
- [x] Add regression coverage so `/runtime/runs/start` returns HTTP 422 for `workflow_run_id` values over 36 characters.

## E. UI Governance Baseline

- [x] Confirm `packages/ui` has package metadata, TypeScript config, source entrypoint, and token stylesheet entry.
- [x] Confirm web Vitest and Playwright configs exist.
- [x] Confirm UI constraint scanner covers route shell length, API route length, runtime fixtures, inline style, arbitrary Tailwind values, cross-feature imports, `<img>`, `console.log`, forbidden UI dependencies, and hand-rolled dialog roles.
- [x] Confirm root component policy keeps reusable app-level components under layout or pushes them into features/packages.
- [x] Record the remaining UI design-system depth as roadmap work rather than pretending current primitives are already a full Radix/cva/Storybook system.

## F. Verification

- [x] Run `pnpm -r list --depth -1`.
- [x] Run `pnpm lint`.
- [x] Run targeted backend regressions for migrations, LLM abstraction, ECC contracts, and runtime start validation.
- [x] Run `pnpm typecheck`.
- [x] Run `pnpm test`.
- [x] Run `pnpm build`.

## G. Residual Roadmap Closure Pass

Completed in the follow-up execution pass:

- [x] Expand `packages/ui` to cover the first 10 primitives:
  Button, Input, Select, Dialog, Sheet, Toast, Table, Tabs, Tooltip, and Badge.
- [x] Use `class-variance-authority` for primitive variants.
- [x] Keep heavy Radix primitives behind `@ai-desk/ui/primitives` so base UI imports do not break route bundle budgets.
- [x] Add `packages/ui/src/primitives.stories.tsx` as the Storybook coverage source for light and dark primitive states.
- [x] Add primitive behavior coverage in `apps/web/tests/unit/ui/primitives.test.tsx`.
- [x] Add axe checks to Playwright e2e through `@axe-core/playwright`.
- [x] Add visual-regression coverage with Playwright screenshot baselines.
- [x] Add route bundle budget enforcement through `scripts/check-web-quality-gates.mjs`.
- [x] Wire web quality gates into `pnpm build` and `.github/workflows/e2e.yml`.
- [x] Replace all app-side direct `fetch` calls with `webFetch` / `apiFetch` from `apps/web/lib/api-client.ts`.
- [x] Add frontend trace header propagation for `X-Trace-ID` and W3C `traceparent`.
- [x] Enforce no direct frontend `fetch` outside `lib/api-client`.
- [x] Add `datamodel-code-generator` to the API dev toolchain.
- [x] Add `pnpm openapi:python-models` to generate OpenAPI-derived Python models.
- [x] Commit generated Python models under `api/generated_contracts`.
- [x] Add contract regression coverage proving generated Python models exist.
- [x] Add explicit Rego policy files for workspace allowlist, tool allowlist, and write gate.
- [x] Extend the OPA facade to evaluate `workspace_allowlist`, `tool_allowlist`, and `write_gate` policies.
- [x] Add OPA regression tests for tool and write gates.
- [x] Extend import boundary checks so `domain/**` and `kernel/**` cannot import concrete integrations.
- [x] Extend import boundary checks so `integrations/**` cannot depend on router modules.

External deployment prerequisites, not local repository tasks:

- Production OPA sidecar deployment and policy bundle promotion.
- External trace backend deployment and dashboard wiring.
- Full page-by-page UX redesign beyond the first primitive and gate baseline.
