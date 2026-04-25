# ai-desk web

`apps/web` is the Next.js App Router frontend for the universal autonomy desk.

Current lanes represented here:

- `FE-1`: workspace shell and project entry placeholders
- `FE-2`: runtime timeline, task graph, task detail, and telemetry views
- `FE-3`: approval center, artifact viewer, ops/evidence panel, shared providers, and UI primitives

Current scaffold reality (2026-04-19):

- `review` / `artifacts` / `ops` pages 现在优先走 `@ai-desk/contracts-api` 生成 client 直连 FastAPI，失败时回退 fixture
- `projects` 现在由 web-side API routes 先代理真实 control-plane，再回退本地 project store
- `runs` / `telemetry` 数据源当前仍以 fixture 为主（等待 runtime read API 直连切换）

## Key Routes

- `/review`
- `/review/[approvalId]`
- `/artifacts`
- `/artifacts/[artifactId]`
- `/ops/attempts/[attemptId]`
- `/projects/[projectId]`
- `/projects/[projectId]/runs/[runId]`
- `/runs/[runId]`
- `/runs/[runId]/timeline`
- `/runs/[runId]/tasks/[taskId]`
- `/runs/[runId]/telemetry`

## Data Strategy

- `review|artifacts|ops`:
  - generated OpenAPI client first
  - fallback to local fixtures when request fails
- `projects`:
  - served by `/app/api/projects/*` local route handlers
  - backed by `features/projects/server/project-store.ts`
- `runs/observability`:
  - currently fixture-backed async loaders

## Commands

```bash
pnpm --filter @ai-desk/web dev
pnpm --filter @ai-desk/web build
pnpm --filter @ai-desk/web test
```
