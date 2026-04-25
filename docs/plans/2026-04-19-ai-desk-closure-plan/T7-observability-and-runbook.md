# T7 Observability / Readiness / Runbook 收口

- 优先级：`P2`
- 目标：让系统从“代码存在”变成“出了问题能定位、能启动、能排查”

---

## 1. 当前问题

当前 readiness 还不完整：

- `/Users/admin/Desktop/ai-desk/apps/api/api/health/router.py`

问题包括：

1. 只检查 DB + Temporal。
2. 不检查 Codex/OpenHands/OpenViking 外部依赖。
3. 没有统一运行说明和故障排查 runbook。
4. observability 目录仍是 placeholder。

---

## 2. 技术实施方案

### A. 扩展 readiness

新增可选依赖探测：

1. Codex app server
2. OpenHands API
3. OpenViking MCP

返回结构区分：

1. required dependency
2. optional dependency
3. degraded reason

### B. 增加 structured logging / correlation

统一日志字段：

1. `workflow_run_id`
2. `task_id`
3. `attempt_id`
4. `trace_id`
5. `provider_request_id`

### C. 增加 metrics

至少补：

1. workflow start / success / failure count
2. claim reclaim count
3. executor success / retryable / terminal failure count
4. approval pending count
5. memory recall/write hit rate

### D. 写 runbook

明确：

1. 如何启动 Postgres / Temporal / worker / API / web
2. 如何验证 Codex / OpenHands / OpenViking
3. readiness / smoke / test 命令
4. 常见故障定位路径

---

## 3. 验收标准

1. health/ready 能反映关键依赖状态。
2. 日志和 metrics 能串起 run/task/attempt/provider。
3. runbook 足够让别人独立启动和排障。

---

## 4. 建议测试

1. 外部依赖关闭时 readiness 返回 degraded 且原因正确。
2. 关键执行路径日志包含 correlation ids。
3. smoke 文档命令可复现。
