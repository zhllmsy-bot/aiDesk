# AI Desk API

统一 `FastAPI` 入口，内部承载多条 lane：

- `api/auth`、`api/control_plane`：BE-1 control plane / auth / migrations
- `api/workflows`、`api/agent_runtime`、`api/events`：BE-2 runtime surface
- `api/executors`、`api/context`、`api/memory`、`api/review`、`api/security`：BE-3 execution / evidence surface

当前骨架状态（2026-04-19）：

- runtime 读写主路径已切到持久化模型（workflow/task/attempt/claim/event/projector）
- review（approval/artifact/attempt/evidence）已落库，不再依赖纯内存对象
- context 支持 `build` 与 `assemble` 双入口（records 查询 + 分层拼装）
- memory 已包含 write governance、ranking 与 OpenViking adapter fallback
- health/readiness 已覆盖 required（DB/Temporal）+ optional（Codex/OpenHands/OpenViking）
- runtime notification adapter 支持 Feishu/Lark（可选启用）

## Local Commands

```bash
uv sync --project apps/api --dev
pnpm --filter @ai-desk/api migrate
pnpm --filter @ai-desk/api dev
pnpm --filter @ai-desk/api worker:runtime
pnpm --filter @ai-desk/api test
pnpm --filter @ai-desk/api test:temporal
pnpm --filter @ai-desk/api eval:runtime
pnpm --filter @ai-desk/api openapi:export
```

`pnpm --filter @ai-desk/api openapi:export` 只导出 BE-1 control plane/auth contract snapshot。
仓库根命令 `pnpm openapi:export` 会额外同步 full-surface OpenAPI 到
`packages/contracts/api/openapi/full.openapi.json`，并生成
`packages/contracts/api/src/generated/schema.ts`。

## BE-3 Surface

- `GET /contracts/execution`
- `GET /executors/capabilities`
- `POST /executors/dispatch`
- `POST /context/build`
- `POST /context/assemble`
- `POST /memory/writes`
- `GET /memory/hits`
- `GET /review/approvals`
- `GET /review/approvals/{approval_id}`
- `POST /review/approvals/{approval_id}/resolve`
- `GET /review/artifacts`
- `GET /review/artifacts/{artifact_id}`
- `GET /review/evidence/{attempt_id}`
- `GET /review/attempts`
- `GET /review/attempts/{attempt_id}`

## Runtime Surface

- `POST /runtime/runs/start`
- `POST /runtime/runs/{workflow_run_id}/approval`
- `GET /runtime/runs/{workflow_run_id}/timeline`
- `GET /runtime/runs/{workflow_run_id}/graph`
- `GET /runtime/tasks/{task_id}/attempts`
- `GET /runtime/workers/health`
- `POST /runtime/recovery/reclaim-stale`
- `POST /runtime/dev/bootstrap`（仅开发）

## Regression Harness

- `pnpm --filter @ai-desk/api eval:runtime`
- `pnpm --filter @ai-desk/api test:temporal`
- `GET /observability/evals/runtime-regression`

这套 harness 当前用于持续验证：

- LangGraph durable interrupt/resume
- security write approval gate
- OpenHands runtime 默认配置安全性
- workflow approval wait/resume 语义
- app restart 后 runtime / review / memory 持久恢复
- 真实 Temporal test environment 下的 approval signal/resume 主路径

## Feishu/Lark Notification

支持两种发送模式（默认都保留内存 adapter）：

1. 直连 Feishu API（`lark-oapi`）：

```bash
AI_DESK_FEISHU_NOTIFICATION_ENABLED=true
AI_DESK_FEISHU_APP_ID=cli_xxx
AI_DESK_FEISHU_APP_SECRET=xxx
AI_DESK_FEISHU_DOMAIN=https://open.feishu.cn
AI_DESK_FEISHU_DEFAULT_RECEIVE_ID=oc_xxx
AI_DESK_FEISHU_RECEIVE_ID_TYPE=chat_id
```

2. 复用本地 Feishu MCP Bridge（推荐，避免在本服务重复封装）：

```bash
AI_DESK_FEISHU_MCP_BRIDGE_ENABLED=true
AI_DESK_FEISHU_MCP_BRIDGE_DIR=/Users/admin/Desktop/feishu_mcp
AI_DESK_FEISHU_MCP_ENV_FILE=/Users/admin/Desktop/feishu_mcp/.env
AI_DESK_FEISHU_MCP_TIMEOUT_SECONDS=30
AI_DESK_FEISHU_DEFAULT_RECEIVE_ID=oc_xxx
AI_DESK_FEISHU_RECEIVE_ID_TYPE=chat_id
```

当 MCP bridge 模式开启时，会优先走 bridge 发送；若未开启 bridge，再按直连配置发送。

若未配置 `AI_DESK_FEISHU_DEFAULT_RECEIVE_ID`，可在消息 metadata 中传入 `receive_id`。
可选地传入 `notification.feishu.receive_id_type` 覆盖默认 `chat_id`（例如 `open_id` / `user_id`）。
