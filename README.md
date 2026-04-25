# AI Desk

通用项目自治平台的 monorepo（runtime + execution + review + workspace web）。

当前仓库并行 lane 的 v1 基线：

- `BE-1`：repo 底座、control plane、auth、Postgres migration、project contracts
- `BE-2`：Temporal workflow、runtime durability、event projector、worker
- `BE-3`：execution / review / evidence / memory / security contract 与 API surface
- `FE-3`：shared web shell、review / artifacts / ops / runs surface

## Layout

```text
apps/
  api/                         FastAPI monolith entry for control plane + runtime + execution
  web/                         Next.js App Router workspace
packages/
  contracts/api/               Full FastAPI OpenAPI snapshot + generated TS client/types
  contracts/projects/          BE-1 owner
  contracts/runtime/           BE-2 owner
  contracts/execution/         BE-3 owner
  ui/                          FE-3 owner
infra/
  dev/                         Postgres + Temporal + worker boot
  deploy/                      Container deployment skeleton
  observability/               Shared observability placeholder
docs/specs/                    Shared spec skeletons
```

## Quick Start

```bash
cp .env.example .env.local
pnpm install
uv sync --project apps/api --dev
pnpm dev
```

`pnpm dev` 会：

1. 拉起 `Postgres`、`Temporal`、`Temporal UI`
2. 执行 Alembic migration
3. 启动 `apps/api`
4. 启动 `apps/web`
5. 启动 runtime worker

## Root Commands

- `pnpm dev`
- `pnpm build`
- `pnpm lint`
- `pnpm typecheck`
- `pnpm test`
- `pnpm db:migrate`
- `pnpm openapi:export`
- `pnpm smoke`

## API Surface

Control plane / auth:

- `GET /health/live`
- `GET /health/ready`
- `POST /auth/register`
- `POST /auth/sessions`
- `GET /auth/me`
- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}`
- `POST /projects/{project_id}/archive`
- `GET /projects/{project_id}/iterations`
- `GET /projects/{project_id}/plan-summary`

Runtime / execution:

- `POST /runtime/runs/start`
- `POST /runtime/runs/{workflow_run_id}/approval`
- `GET /runtime/runs/{workflow_run_id}/timeline`
- `GET /runtime/runs/{workflow_run_id}/graph`
- `GET /runtime/tasks/{task_id}/attempts`
- `GET /runtime/workers/health`
- `POST /runtime/dev/bootstrap`
- `POST /runtime/recovery/reclaim-stale`
- `GET /notifications/deliveries`
- `GET /contracts/execution`
- `GET /executors/capabilities`
- `POST /executors/dispatch`
- `POST /context/build`
- `POST /context/assemble`
- `POST /memory/writes`
- `GET /memory/hits`
- `GET /observability/runtime-sla`
- `GET /review/approvals`
- `GET /review/approvals/{approval_id}`
- `POST /review/approvals/{approval_id}/resolve`
- `GET /review/artifacts`
- `GET /review/artifacts/{artifact_id}`
- `GET /review/evidence/{attempt_id}`
- `GET /review/attempts`
- `GET /review/attempts/{attempt_id}`

### `project.audit` Default Mode

`project.audit` 现在默认采用三段式评估范式（对齐 `project-maturity-audit`）：

1. `audit-survey`（`auditor`）：构建证据地图并给出初步闭环判断
2. `audit-counter-argument`（`reviewer`）：反驳乐观结论，识别伪闭环与脆弱点
3. `audit-roadmap`（`planner`）：输出优先级收口路线图

说明：

- 若 `/runtime/runs/start` 请求未显式传入 `tasks`，`project.audit` 会自动注入上述三段任务。
- 请求 `metadata.audit_mode` 默认写入 `three_pass`，用于前端与报告面识别评估模式。

### `project.improvement` Drive Modes

`project.improvement` 支持两种驱动模式：

1. `self_driven`（默认）：按 `project-maturity-audit` 范式循环迭代
2. `external_requirement`：按外部明确需求做交付闭环

`self_driven` 默认行为：

- `metadata.drive_mode` 默认 `self_driven`
- `metadata.loop_iterations` 默认 `2`（范围 `1..5`）
- 每轮执行固定序列：
  - `survey` -> `counter-argument` -> `roadmap` -> `execution` -> `review`
- `metadata.evaluation_pattern=project_maturity_audit.three_pass`

`external_requirement` 默认行为：

- 固定序列：`req-clarify` -> `req-execution` -> `req-review`
- `metadata.evaluation_pattern=external_requirement.delivery`
- 若调用方显式传入 `tasks`，runtime 保留调用方定义，不覆盖。

### Feishu Notification Integration

runtime completion notification 已支持通过 Feishu/Lark IM 发送。默认仍保留内存 adapter；启用 Feishu 后会并行投递到 Feishu。

环境变量：

```bash
AI_DESK_FEISHU_NOTIFICATION_ENABLED=true
AI_DESK_FEISHU_APP_ID=cli_xxx
AI_DESK_FEISHU_APP_SECRET=xxx
AI_DESK_FEISHU_DOMAIN=https://open.feishu.cn
AI_DESK_FEISHU_DEFAULT_RECEIVE_ID=oc_xxx
AI_DESK_FEISHU_RECEIVE_ID_TYPE=chat_id
```

说明：

- `AI_DESK_FEISHU_DEFAULT_RECEIVE_ID` 未配置时，可在 runtime 通知 metadata 中传 `receive_id`。
- 可在 runtime 请求 metadata 里传 `notification.feishu.receive_id_type` 覆盖默认 `chat_id`。
- 发送失败不会中断 workflow 主流程，会返回 failed receipt 并写入活动结果。
- 所有通知投递结果都会落入 durable `notification_deliveries` ledger，可通过 `GET /notifications/deliveries` 查询。

### Memory Backbone

memory 现在按 `Mem0 -> OpenViking -> local` 的优先级选择 provider：

- 配置 `AI_DESK_MEM0_API_KEY` 时，优先使用 `Mem0` 作为外部 memory backbone
- 未配置 `Mem0` 时，回落到现有 `OpenViking` / 本地持久化路径
- `/memory/writes` 与 `/memory/hits` 的 API surface 不变，上层 workflow / context 侧无需改写

环境变量：

```bash
AI_DESK_MEM0_API_KEY=
AI_DESK_MEM0_API_URL=https://api.mem0.ai
```

### Break-Glass Full Access（按次执行）

当前仓库已取消进程级 `full access` 总开关，默认策略是 `safe-by-default`。

如需在可信环境下做一次性的 break-glass 执行，可在单次 runtime 请求 metadata 中显式传：

```json
{
  "runtime_full_access": true
}
```

说明：

- 该能力只对当前 run 生效，不会污染进程全局状态
- 默认仍保留 security gate、workspace allowlist、审批流
- 只有显式携带 `metadata.runtime_full_access=true` 时，workflow 才会构造放宽的 executor permission policy

### Runtime Regression Harness

仓库现在内置一套轻量回归 harness，用于持续验证 runtime / security / executor 的关键闭环：

```bash
pnpm eval:runtime
```

如需跑真实 Temporal test environment 下的 durable approval 主路径回归：

```bash
pnpm test:temporal
```

当前 suite 覆盖：

- LangGraph interrupt/resume durable path
- LangGraph resume now restores by durable `checkpoint_id`, not legacy checkpoint dict handoff
- security write approval gate
- OpenHands runtime 默认必须显式配置 remote 或本地 fallback
- workflow approval wait/resume semantics
- restart durability for runtime timeline, approval, and memory state
- real Temporal start -> signal approval -> resume -> complete path

API 也提供只读入口：

- `GET /observability/evals/runtime-regression`
- `GET /observability/runtime-sla`

## Notes

- `pnpm openapi:export` 现在会同时导出：
  - `packages/contracts/projects/openapi/control-plane.openapi.json`
  - `packages/contracts/api/openapi/full.openapi.json`
  - `packages/contracts/api/src/generated/schema.ts`
- `packages/contracts/api` 是新的 OpenAPI-first 合同包，供 web 复用生成的 TS client/types。
- `packages/contracts/execution` 现在提供 FE-3 消费的 review / artifact / ops TS contract，同时补齐 executor input/result schema。
- Runtime timeline / graph / attempts / workers 读模型已由持久化 projector 统一提供。
- `infra/dev/run-worker.sh` 已固定到 runtime worker 入口，后续 worker 演进不再改启动路径。
