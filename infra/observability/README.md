# Observability Scaffold

当前目录仍然是基础骨架，但 runtime 观测已在 API 内形成可用最小集：

1. `/health/live` + `/health/ready`（required/optional 依赖分层）
2. `/observability/metrics`（in-process counters/gauges 快照）
3. correlation middleware（trace/request id 透传）
4. runtime event/read-model（timeline/graph/attempt/worker health）

## 当前边界

1. 这里不包含独立 collector/agent 部署编排
2. trace/export pipeline 仍未接入外部 APM backend
3. 指标当前以内存 collector 为主，重启后不保留

## 参考实现

- `apps/api/api/health/router.py`
- `apps/api/api/observability/metrics.py`
- `apps/api/api/observability/middleware.py`
- `apps/api/api/runtime_persistence/projectors.py`
