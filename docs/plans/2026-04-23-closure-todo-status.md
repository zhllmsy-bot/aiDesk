# 2026-04-23 全局闭环 TODO 自检（本地版本）

- 仓库：`/Users/admin/Desktop/ai-desk`
- 目的：将你之前提出的 P0/P1 收口项做一次“全局自检 + 是否闭合”复核，并给出可执行待办。
- 最新验证（2026-04-23）：仓库级发布门已恢复全绿
  - `pnpm lint`：全绿（含 OpenAPI snapshot 格式化）
  - `pnpm typecheck`：全绿
  - `pnpm test`：`@ai-desk/api: 157 passed, 8 skipped`；`@ai-desk/web: 22 passed`

## 1) 已关闭（直接可验）

- 全局 full access（进程级默认）已拆除。`runtime_full_access` 仅保留为 `metadata` 层运行时能力信号，不作为默认全局开关。
- Approval durable bridge 已闭合：`workflows/approval_bridge.py` 与 `workflows/router.py` 形成 signal 入口，`base.py` 实现等待/恢复语义，相关 e2e 用例通过。
- LangGraph 官方持久化接入已完成：`api/integrations/langgraph.py` + `api/agent_runtime/service.py` 使用官方 checkpointer（Postgres 时优先 `PostgresSaver`）。
- OpenHands 官方 runtime 接口已对齐到 SDK 工作区抽象：`api/executors/openhands_runtime.py` 与 `api/executors/providers/openhands.py` 基于 `Workspace` 抽象运行，去除长周期自定义协议依赖。
- Memory backbone 已切到 `Mem0/OpenViking` adapter 链路：`memory/service.py`、`memory/ranking.py`、`memory/governance.py` 与 `integrations` 健康探针收口。
- Runtime durability 主链路通过迁移与回归验证：`runtime_persistence` 表模型、review/evidence/artifact/attempt/evidence 读写都落库。
- Notification delivery ledger 已 durable 化并开放查询面：`notifications/service.py`、`notifications/router.py`、`runtime_persistence/models.py`、`tests/test_notification_product_surfaces.py`。
- Runtime SLA 读模型已独立暴露：`observability/router.py` 新增 `/observability/runtime-sla`，支持审批耗时、失败恢复、重试恢复、通知投递聚合。
- 执行策略抽象已从 workflow base 中收敛出 `WorkflowExecutionPolicy`，`base.py` 不再直接拼接 permission policy 与 workspace 派发细节。

## 2) 已完成的遗留修复（最近）

- 使 `tests/test_executor_provider_artifacts.py` 全部通过，修正 Codex 模拟分支的验证元数据与模拟转录可观察性。
- 统一 `verification` 分支元数据，`runtime` 与 `execution` 验证 artifact 生成行为回归稳定。

## 3) 本轮已完成收口（原 P1/P2）

1. `runtime` / `execution` 模块边界继续收敛：
   - 新增 `workflows/orchestration.py`，将 context 组装 payload 与通知回执汇总从 `workflows/definitions/base.py` 抽离。
2. 通知 provider 级重试与回执状态回写：
   - `NotificationService` 支持 adapter 级重试（可配置 attempts/backoff）；
   - 新增 `NotificationHistoryService.update_delivery_status(...)`；
   - 新增 `POST /notifications/deliveries/{receipt_id}/status` 用于 webhook/pullback 回写最终送达态。
3. SLA 项目/迭代维度聚合与前端消费：
   - `runtime_sla_snapshot` 支持 `project_id / iteration_id / bucket_minutes`；
   - `/observability/runtime-sla` 已接入上述过滤与趋势参数；
   - 返回体包含 `scope` 与 `trend.points`，可直接供前端趋势图消费；
   - `apps/web/features/observability/hooks/use-runtime-sla.ts` 与 `run-telemetry-screen.tsx` 已接入 SLA 卡片和趋势列表；
   - 回归通过：`apps/web/tests/unit/observability/run-telemetry-screen.test.tsx`。

## 4) 本轮发布门修复（新增）

- 修复 OpenAPI snapshot 漂移导致的 contract 门禁失败：
  - 重新导出并同步：
    - `packages/contracts/projects/openapi/control-plane.openapi.json`
    - `packages/contracts/api/openapi/full.openapi.json`
    - `apps/api/tests/contracts_snapshots/openapi-full.json`
  - 全量验证：`pnpm lint && pnpm typecheck && pnpm test` 全绿。

## 5) 后续增量（非阻断）

- 30 天：补通知回写来源鉴权与幂等签名，防止外部伪造回执。
- 60 天：为趋势指标补告警阈值与自动化巡检（例如失败率、审批耗时异常）。
- 90 天：补多租户隔离与分层 SLA（按 workspace / project tier）。
- 飞书通知补充：当前本地 `.env.local` 中 `AI_DESK_FEISHU_NOTIFICATION_ENABLED=false` 且凭据为空，暂无法执行真实外发；待配置后可立即补发链路通知。
