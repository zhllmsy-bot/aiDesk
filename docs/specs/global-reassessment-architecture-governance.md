# aiDesk Global Reassessment Spec

Date: 2026-04-26
Status: Executable spec
Scope: architecture, modules, contracts, UI constraints, OSS adoption, and long-term maintainability

## 1. Decision

aiDesk remains a modular monolith around Temporal durable orchestration, LangGraph stateful agent execution, FastAPI control surfaces, and a Next.js operator console.

The project should not become another agent SDK. Its durable value is the control plane above agent runtimes: project state, workflow state, approvals, security policy, evidence, artifacts, memory governance, notifications, and operator observability.

## 2. Current Evidence Baseline

Verified present in the repository:

- Root workspace and tooling: `pnpm-workspace.yaml`, `tsconfig.base.json`, `biome.json`, root `package.json` scripts.
- CI gates: `.github/workflows/ci.yml`, `.github/workflows/contracts.yml`, `.github/workflows/e2e.yml`.
- Contract packages: `packages/contracts/{api,projects,runtime,execution,llm}` with package metadata and source entrypoints.
- Runtime durability: Temporal workflow entrypoints, runtime persistence models, event store, projectors, timeline, graph, attempts, approvals, artifacts, worker health.
- LLM and agent abstraction: `packages/contracts/llm`, `api/integrations/llm`, executor provider facade, Claude/OpenAI/Aider/agent-harness provider slots.
- Kernel/integration boundary seeds: `api/kernel/langgraph`, `api/integrations/memory`, `api/domain/context`, `api/domain/security`.
- Policy/observability seeds: `infra/policies/execution.rego`, `api/security/opa.py`, `api/observability/otel.py`.
- Web gates: `apps/web/vitest.setup.ts`, `apps/web/playwright.config.ts`, custom import/UI constraint scripts.

## 3. Architecture Boundaries

### 3.1 Kernel

Kernel code owns non-replaceable runtime semantics:

- event schemas and event-store semantics
- LangGraph checkpoint factory
- runtime persistence/projector model
- workflow state machine concepts

Kernel code must not import concrete third-party providers from `integrations/**`.

### 3.2 Integrations

Integration code owns replaceable provider details:

- LLM SDKs and LiteLLM/instructor adapters
- memory providers such as Mem0 and OpenViking
- executor provider adapters such as OpenHands, Codex, Claude Code, Aider, Claude Agent SDK, OpenAI Agents SDK
- notification sinks such as Feishu and future Apprise

Third-party SDK imports must stay inside integration/provider folders or explicit compatibility shims.

### 3.3 Domain

Domain code owns aiDesk business rules:

- approval semantics
- context assembly and ContextSkill selection
- memory governance/ranking
- break-glass and tool hook policy facade
- notification delivery history

Domain code may depend on protocols and contracts, not concrete SDK clients.

### 3.4 Applications

Applications wire modules and expose IO:

- `apps/api/api/app.py` registers routers and builds runtime containers.
- `apps/web/app/**` remains a thin route shell.
- `apps/web/features/<domain>/**` owns feature-local API hooks, components, view models, and schemas.

## 4. Contract Governance

OpenAPI is the public API truth source. Generated artifacts and snapshots are regression evidence, not hand-edited sources.

Required gates:

- OpenAPI export must update `packages/contracts/api/openapi/full.openapi.json`.
- Contract snapshot tests must fail on drift.
- Runtime and execution JSON snapshots are read-only compatibility evidence.
- LLM/Agent contracts live in `packages/contracts/llm` until they are promoted into OpenAPI routes.
- Python service code must not bypass integration boundaries to call LLM SDKs directly.

## 5. UI Governance

The UI system is governed by machine-enforced constraints before further page expansion.

Closed stack:

- Styling: Tailwind-compatible CSS variables and token classes.
- Headless behavior: Radix primitives for complex widgets.
- Variants: cva/tailwind-variants compatible variant APIs.
- Icons: Lucide.
- Server state: TanStack Query.
- Local state: React local state only unless an ADR approves otherwise.
- Forms: React Hook Form plus zod when schema complexity justifies it.

Non-negotiable constraints:

- No cross-feature imports.
- `app/**/page.tsx` stays at or below 20 lines.
- `app/api/**/route.ts` stays at or below 60 lines.
- Runtime fixtures stay out of production source.
- No inline style, arbitrary Tailwind values, `<img>`, `console.log`, or hand-rolled dialog roles.
- Shared reusable UI moves to `packages/ui`.
- PRs touching UI must list the primitives used and any ADR-backed exemptions.

## 6. Security And Policy

Security decisions must become versioned policy inputs rather than scattered conditionals.

Required policy surfaces:

- break-glass reason validation
- workspace allowlist
- tool allowlist
- write gate
- hook decisions
- approval audit projection

Break-glass remains per-run and explicit. Runtime full access must not be a process-wide default.

## 7. Observability

Trace identity must be carried through web, API, worker, executor, and LLM provider paths.

Required evidence for a runtime run:

- timeline and graph
- task attempts
- approval decisions
- artifacts and evidence refs
- memory recall/write records
- notification delivery ledger
- trace id or degraded local evidence when localhost/DB inspection is unavailable

## 8. Long-Term Roadmap

The next six months remain organized around five structural epics:

1. Engineering governance and release gates.
2. LLM/Agent abstraction and provider replacement.
3. Kernel/integration/domain boundary hardening.
4. UI design system with hard constraints and migration.
5. Policy-based security and native tracing.

These epics are not optional, but they should be executed through small PR-sized changes with tests and acceptance gates.

## 9. Acceptance Criteria

The spec is satisfied for the current baseline when:

- root workspace, CI, contract packages, web test config, and migration chain are present
- `pnpm -r list --depth -1` lists all workspace apps/packages
- `pnpm lint` passes
- targeted backend regressions for migrations, LLM abstraction, ECC contracts, and runtime start validation pass
- `pnpm build` runs the route bundle quality gate
- `pnpm test:e2e` runs axe and visual-regression checks
- OpenAPI-derived Python models are generated through `pnpm openapi:python-models`
- docs/plans include an auditable completion TODO for this reassessment
- PR template forces future changes to declare validation, contract impact, UI primitives, and ADR/exemption links
