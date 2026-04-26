# AI Desk Worker

Dedicated Temporal runtime worker package for ai-desk.

## Commands

```bash
uv sync --project apps/worker --dev
pnpm --filter @ai-desk/worker dev
pnpm --filter @ai-desk/worker lint
pnpm --filter @ai-desk/worker typecheck
```

The worker depends on the sibling `ai-desk-api` package through a local editable source and exposes a stable runtime entrypoint at `python -m ai_desk_worker.runtime`.
