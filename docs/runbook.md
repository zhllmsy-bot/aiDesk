# ai-desk Operations Runbook

## 1. 服务启动

### 1.1 依赖服务

| 服务 | 默认地址 | 必需 | 环境变量 |
|------|----------|------|----------|
| PostgreSQL | `localhost:5432` | 是 | `AI_DESK_DATABASE_URL` |
| Temporal | `localhost:7233` | 是 | `AI_DESK_TEMPORAL_ADDRESS` |
| Codex App Server | `ws://127.0.0.1:8321` | 否 | `AI_DESK_CODEX_APP_SERVER_URL` |
| OpenHands Runtime | `http://127.0.0.1:3001` | 否 | `AI_DESK_OPENHANDS_API_URL` |
| Mem0 API | `https://api.mem0.ai` | 否 | `AI_DESK_MEM0_*` |
| Feishu / Lark Notification | `open.feishu.cn` | 否 | `AI_DESK_FEISHU_*` |
| OpenViking MCP | — | 否 | `AI_DESK_OPENVIKING_MCP_URL` |

### 1.2 启动顺序

```bash
# 一键本地路径：依次拉起 infra、迁移、API、Web、worker
pnpm dev
```

如果需要手工拆分：

```bash
pnpm infra:up
pnpm db:migrate
pnpm --filter @ai-desk/api dev
pnpm --filter @ai-desk/web dev
pnpm --filter @ai-desk/worker dev
```

### 1.3 环境变量

所有环境变量以 `AI_DESK_` 为前缀，运行时默认先读取 `.env`，再用 `.env.local` 覆盖：

```bash
AI_DESK_DATABASE_URL=postgresql+psycopg://ai_desk:ai_desk@localhost:5432/ai_desk
AI_DESK_TEMPORAL_ADDRESS=localhost:7233
AI_DESK_TEMPORAL_NAMESPACE=default
AI_DESK_RUNTIME_TASK_QUEUE=ai-desk.runtime
AI_DESK_RUNTIME_WORKER_ID=runtime-worker
AI_DESK_CODEX_APP_SERVER_TRANSPORT=stdio
AI_DESK_OPENHANDS_API_URL=http://127.0.0.1:3001
AI_DESK_OPENHANDS_LOCAL_WORKSPACE_ENABLED=false
AI_DESK_OPENHANDS_REMOTE_WORKING_DIR=
AI_DESK_MEM0_API_KEY=
AI_DESK_MEM0_API_URL=https://api.mem0.ai
AI_DESK_FEISHU_NOTIFICATION_ENABLED=false
AI_DESK_FEISHU_APP_ID=
AI_DESK_FEISHU_APP_SECRET=
AI_DESK_FEISHU_DOMAIN=https://open.feishu.cn
AI_DESK_FEISHU_DEFAULT_RECEIVE_ID=
AI_DESK_FEISHU_RECEIVE_ID_TYPE=chat_id
AI_DESK_FEISHU_MCP_BRIDGE_ENABLED=false
AI_DESK_FEISHU_MCP_BRIDGE_DIR=/Users/admin/Desktop/feishu_mcp
AI_DESK_FEISHU_MCP_ENV_FILE=/Users/admin/Desktop/feishu_mcp/.env
AI_DESK_FEISHU_MCP_TIMEOUT_SECONDS=30
AI_DESK_OPENVIKING_MCP_URL=
AI_DESK_OTEL_ENABLED=false
AI_DESK_OTEL_SERVICE_NAME=ai-desk-api
AI_DESK_OTEL_EXPORTER_OTLP_ENDPOINT=
AI_DESK_LOGFIRE_ENABLED=false
```

说明：`.env.test` 仅用于测试场景（通过测试代码显式注入），不再作为运行时默认环境文件。

## 2. 健康检查

### 2.1 Liveness

```bash
curl http://localhost:8000/health/live
```

返回示例：
```json
{"service": "api", "status": "ok", "checked_at": "..."}
```

### 2.2 Readiness

```bash
curl http://localhost:8000/health/ready
```

返回示例（全部正常）：
```json
{
  "service": "api",
  "status": "ready",
  "required": {
    "database": {"status": "ok"},
    "temporal": {"status": "ok", "address": "localhost:7233", "namespace": "default"}
  },
  "optional": {
    "codex": {"status": "ok", "note": "stdio transport; binary exists"},
    "openhands": {"status": "ok", "target": "http://127.0.0.1:3001"},
    "feishu": {"status": "not_configured", "reason": "feishu notifications disabled"},
    "openviking": {"status": "not_configured", "reason": "openviking_mcp_url not set"}
  },
  "degraded_reasons": [],
  "checked_at": "..."
}
```

返回示例（degraded）：
```json
{
  "service": "api",
  "status": "degraded",
  "required": {"database": {"status": "ok"}, "temporal": {"status": "ok", ...}},
  "optional": {
    "codex": {"status": "error", "reason": "codex binary not found: ..."},
    "openhands": {"status": "error", "reason": "openhands runtime unavailable at http://127.0.0.1:3001"},
    "feishu": {"status": "error", "reason": "feishu enabled but app_id/app_secret missing"},
    "openviking": {"status": "not_configured", ...}
  },
  "degraded_reasons": [
    "codex: codex binary not found: ...",
    "openhands: openhands runtime unavailable at http://127.0.0.1:3001",
    "feishu: feishu enabled but app_id/app_secret missing"
  ],
  "checked_at": "..."
}
```

**状态判断规则：**
- `ready`：所有 required 依赖正常
- `degraded`：任一 required 依赖异常，或任一 optional 依赖返回 error
- `not_configured` 的 optional 依赖不影响整体状态

### 2.3 Metrics

```bash
curl http://localhost:8000/observability/metrics
```

返回所有计数器和仪表盘的快照。

## 3. 验证外部依赖

### 3.1 Codex

```bash
# stdio 模式：检查 binary 是否存在
ls -la /Applications/Codex.app/Contents/Resources/codex

# websocket 模式：检查连接
curl http://127.0.0.1:8321/health
```

### 3.2 OpenHands

```bash
curl http://127.0.0.1:3001/health
```

默认要求配置 remote runtime。
如需在可信本机环境下启用 host filesystem fallback，必须显式设置：

```bash
AI_DESK_OPENHANDS_LOCAL_WORKSPACE_ENABLED=true
```

### 3.3 OpenViking

```bash
# 如果配置了 MCP URL
curl $AI_DESK_OPENVIKING_MCP_URL
```

### 3.4 Mem0

```bash
# 检查配置是否完整
echo "$AI_DESK_MEM0_API_KEY"
echo "$AI_DESK_MEM0_API_URL"

# readiness 中检查 optional.mem0
curl http://localhost:8000/health/ready | jq '.optional.mem0'
```

### 3.5 Feishu / Lark Notification

```bash
# 检查配置是否完整
echo "$AI_DESK_FEISHU_NOTIFICATION_ENABLED"
echo "$AI_DESK_FEISHU_APP_ID"
echo "$AI_DESK_FEISHU_APP_SECRET"
echo "$AI_DESK_FEISHU_DEFAULT_RECEIVE_ID"
echo "$AI_DESK_FEISHU_MCP_BRIDGE_ENABLED"
echo "$AI_DESK_FEISHU_MCP_BRIDGE_DIR"
echo "$AI_DESK_FEISHU_MCP_ENV_FILE"

# readiness 中检查 optional.feishu
curl http://localhost:8000/health/ready | jq '.optional.feishu'
```

## 4. Smoke / Eval

```bash
# 基础 smoke（不需要外部依赖）
cd apps/api
python -m api.scripts.smoke
```

```bash
# runtime/security/executor regression harness
cd apps/api
python -m api.scripts.eval_harness
```

当前 harness 覆盖：

- LangGraph interrupt/resume
- security write approval gate
- OpenHands remote-first 安全默认
- workflow approval wait/resume
- app restart 后 runtime / review / memory durability

```bash
# 真实 Temporal test environment durable approval 回归
pnpm test:temporal
```

## 5. 常见故障定位

### 5.1 API 启动失败

| 症状 | 排查路径 |
|------|----------|
| `connection refused` 到 DB | 检查 PostgreSQL 是否运行：`pg_isready` |
| Temporal 连接超时 | 检查 Temporal：`temporal workflow list` |
| Alembic 迁移失败 | 检查 DB 连接和迁移版本：`alembic current` |

### 5.2 Workflow 不执行

| 症状 | 排查路径 |
|------|----------|
| Workflow 已创建但停在 QUEUED | 检查 Temporal Worker 是否运行 |
| Task CLAIMED 后无进展 | 检查 executor（Codex/OpenHands）是否可用 |
| CLAIMED → RECLAIMED | Lease 超时，检查 `runtime_lease_timeout_seconds` |

### 5.3 Executor 失败

| 症状 | 排查路径 |
|------|----------|
| Codex transport error | 检查 Codex binary 路径和 websocket 连接 |
| OpenHands runtime unavailable | 检查 OpenHands remote runtime URL、API key，或确认是否显式启用 local fallback |
| `retryable_failure` | 临时性错误，系统会自动重试 |
| `terminal_failure` | 检查日志中的 `reason` 字段 |

### 5.4 Memory 写入失败

| 症状 | 排查路径 |
|------|----------|
| `memory write rejected` | 检查 quality_score 和 dedup 规则 |
| Mem0 write failed | 检查 API key、Mem0 URL 和外网连通性 |
| OpenViking write failed | 检查 MCP URL 配置和网络连通性 |
| Recall 返回空 | 检查 namespace_prefix 和 project_id |

### 5.5 日志中查找 correlation

日志为 JSON 格式，可通过 `jq` 过滤：

```bash
# 按 workflow_run_id 过滤
uvicorn ... 2>&1 | jq 'select(.workflow_run_id == "run-123")'

# 按 task_id 过滤
uvicorn ... 2>&1 | jq 'select(.task_id == "task-1")'

# 按 trace_id 过滤
uvicorn ... 2>&1 | jq 'select(.trace_id != "")'

# 只看错误
uvicorn ... 2>&1 | jq 'select(.level == "ERROR")'
```

### 5.6 Approval 卡住

| 症状 | 排查路径 |
|------|----------|
| Approval 长时间 PENDING | 检查 `runtime_signal_timeout_seconds`（默认 300s） |
| Approval 超时 | Workflow 会自动标记 FAILED |

## 6. 关键配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `runtime_lease_timeout_seconds` | 30 | Task claim 的租约超时 |
| `runtime_signal_timeout_seconds` | 300 | Approval 等待超时 |
| `openhands_local_workspace_enabled` | false | 是否允许 OpenHands 退回到本机 workspace；默认关闭以保持 remote-first |
| `codex_app_server_startup_timeout_seconds` | 20 | Codex 启动超时 |
| `codex_app_server_turn_timeout_seconds` | 1800 | Codex 单轮执行超时 |
| `session_ttl_hours` | 12 | 用户会话 TTL |
