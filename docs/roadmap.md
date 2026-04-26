# Roadmap

AI Desk is aimed at becoming an enterprise project-level autonomy backbone, not another agent CLI. The core differentiation is durable orchestration around project audits, improvement runs, approvals, executor policy, evidence, memory, and observability.

## v0.1 Self-Hosted Beta

Goal: one operator can self-host AI Desk, import or select a project, run a three-pass audit, inspect the audit canvas, review artifacts, and follow runtime proof through Temporal-backed events.

Required:

- local `pnpm dev` first-run path
- dedicated project audit canvas
- runtime timeline and task graph
- review, artifact, and ops surfaces
- LLM and executor provider boundaries
- UI hard constraints in CI
- OpenAPI contract diff gate
- OTel/logfire instrumentation path, default off

## v0.2 Multi-Tenant Alpha

Goal: teams can operate multiple projects with clearer tenancy, policy bundles, and provider governance.

Required:

- tenant/project role model hardening
- policy decision ledger
- production OPA sidecar or equivalent policy bundle flow
- trace backend and dashboard wiring
- provider cost and budget ledger
- guided demo project import
- richer audit report export

## v0.3 Managed/SaaS Readiness

Goal: AI Desk can run as a managed control plane while preserving self-hosted deployment as a first-class path.

Required:

- billing and usage boundaries
- hosted secrets and provider connection management
- external webhook/event integrations
- organization-level observability
- backup, restore, and disaster recovery runbooks
- public beta onboarding flow

## Non-Goals

- Competing with Claude Code, Codex, OpenHands, or Aider as an interactive CLI.
- Hiding executor provenance from operators.
- Treating LLM provider SDKs as domain abstractions.
