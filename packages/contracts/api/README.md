# `@ai-desk/contracts-api`

Generated TypeScript contract package for the full FastAPI surface.

## Workflow

```bash
pnpm openapi:export
```

That command:

1. exports the control-plane OpenAPI snapshot
2. exports the full API OpenAPI snapshot to `openapi/full.openapi.json`
3. regenerates `src/generated/schema.ts`

Use `createApiClient()` for thin, typed consumers in `apps/web` instead of hand-writing fetch
contracts per route.
