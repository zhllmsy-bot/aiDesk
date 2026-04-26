# Observability Scaffold

当前目录仍然是基础骨架，但 runtime 观测已在 API 内形成可用最小集：

1. `/health/live` + `/health/ready`（required/optional 依赖分层）
2. `/observability/metrics`（in-process counters/gauges 快照）
3. correlation middleware（trace/request id 透传）
4. OpenTelemetry Python SDK + FastAPI instrumentation（默认关闭）
5. logfire FastAPI instrumentation（默认关闭且不外发）
6. runtime event/read-model（timeline/graph/attempt/worker health）

## 本地启用

默认不要求本机运行 collector。需要本地 span provider 时：

```bash
AI_DESK_OTEL_ENABLED=true
AI_DESK_OTEL_SERVICE_NAME=ai-desk-api
```

需要向 OTLP HTTP collector 导出时：

```bash
AI_DESK_OTEL_ENABLED=true
AI_DESK_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
```

需要打开 logfire instrumentation 时：

```bash
AI_DESK_LOGFIRE_ENABLED=true
```

## 当前边界

1. 这里不包含独立 collector/agent 部署编排
2. trace/export pipeline 需要显式配置 `AI_DESK_OTEL_EXPORTER_OTLP_ENDPOINT`
3. 指标当前以内存 collector 为主，重启后不保留

## 参考实现

- `apps/api/api/health/router.py`
- `apps/api/api/observability/metrics.py`
- `apps/api/api/observability/middleware.py`
- `apps/api/api/observability/otel.py`
- `apps/api/api/runtime_persistence/projectors.py`
