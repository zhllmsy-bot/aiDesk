# Contributing

AI Desk is a self-hosted project autonomy backbone. Contributions should preserve the main product contract: durable runtime state, auditable approvals, replaceable agent providers, and a disciplined web surface.

## Local Setup

```bash
cp .env.example .env.local
pnpm install
uv sync --project apps/api --dev
pnpm dev
```

Use `AI_DESK_SKIP_INFRA=1 pnpm dev` when you only need the web app and do not want to start local Postgres or Temporal.

## Before Opening A Pull Request

Run the same gates used by CI:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm test:e2e
```

If API contracts changed, also run:

```bash
pnpm openapi:export
pnpm openapi:python-models
```

Then confirm that generated contract diffs are intentional.

## Boundaries

- `apps/api/api/kernel/**` owns durable runtime infrastructure.
- `apps/api/api/integrations/**` owns concrete SDKs and external adapters.
- `apps/api/api/domain/**` owns business policy and orchestration concepts.
- `packages/contracts/**` owns cross-language contract types.
- `packages/ui` owns UI primitives and tokens.
- `apps/web/features/**` owns feature screens and must not import sibling features directly.

Concrete LLM SDK imports belong only under `apps/api/api/integrations/llm/**`.

## Web And UI Rules

Use `@ai-desk/ui` primitives and token-backed classes. Do not hand-roll dialogs, arbitrary Tailwind values, inline styles, direct Radix imports in `apps/web`, direct `fetch`, `<img>`, or cross-feature imports. These are enforced by `pnpm lint`.

Route files under `apps/web/app/**/page.tsx` should stay as thin shells. Move actual UI into feature components.

## Tests

Keep tests near the risk:

- API behavior: `apps/api/tests`
- Web unit behavior: `apps/web/tests/unit`
- Browser smoke and visual/a11y gates: `apps/web/tests/e2e`
- Contract snapshots: `apps/api/tests/contracts_snapshots` and `packages/contracts/api`

## Documentation

Update `README.md`, `docs/runbook.md`, or `docs/roadmap.md` when a change affects first-run setup, deployment expectations, public positioning, or release scope.
