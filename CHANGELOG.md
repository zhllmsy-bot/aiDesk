# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog, and this project follows semantic versioning once tagged releases begin.

## [0.1.0] - 2026-04-26

### Added

- Contract-first FastAPI control plane with runtime, review, evidence, memory, and observability surfaces.
- Temporal-backed runtime durability, approval ledger, and project-improvement workflow backbone.
- Shared `@ai-desk/ui` primitives, tokens, manifest generation, and CI quality gates for lint, style, accessibility, and visual regression.
- Dedicated `apps/worker` Python package with its own `pyproject.toml`, runtime entrypoint, and Dockerfile.

### Changed

- Promoted `next-intl` from installed-only to active app wiring with request config and locale messages.
- Enforced UI governance with AST-backed ESLint rules, Stylelint token checks, and route bundle budgets.
- Marked stub agent-loop providers explicitly and blocked them from factory selection.
- Wired API and worker observability through OpenTelemetry startup hooks plus outbound `httpx` instrumentation.

### Notes

- Current baseline is a self-hosted beta-quality control room focused on project audit, review, and runtime inspection.
