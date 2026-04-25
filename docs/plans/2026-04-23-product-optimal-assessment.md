# 2026-04-23 产品最优视角评估与收口结果

## 1. 总结结论

- 结论：当前项目整体设计**合理且可商业化演进**，核心链路已具备“可执行、可观测、可恢复、可治理”四要素。
- 相比热门开源 Agent 框架，当前方案的优势在于：
  - 将 `runtime durability`、`approval`、`security gate`、`artifact/evidence` 一体化落库；
  - 把“平台可运营性”作为一等公民（timeline/graph/attempt/worker health/notification/SLA）。
- 当前阶段产品最优策略：继续保持“复用官方能力 + 自有业务治理层”模式，不做框架重写。

## 2. 与热门开源方案对比（产品维度）

### 2.1 Agent 编排

- 现状：
  - 工作流调度已支持 `depends_on` DAG、重试、退避、审批中断恢复；
  - `project.improvement` 默认 `self_driven` 并支持多轮审视/反证/执行/复盘。
- 对比：
  - 对齐了 `LangGraph` 的状态机与持久化思路；
  - 对齐了 `Temporal` 的 durable orchestration 思路；
  - 在“生产治理能力”上比纯对话式框架更完整。
- 结论：编排层是可上线的，不建议改回轻量手写调度器。

### 2.2 上下文管理

- 现状：
  - `ContextAssemblyService` 已接入 runtime 默认调度路径；
  - 非强依赖 `metadata.context_blocks` 手工注入，支持自动组装与预算控制。
- 对比：
  - 比多数开源默认 RAG 拼装更可控（token budget / block 层级）。
- 结论：上下文策略方向正确，应继续强化质量评估而非重写机制。

### 2.3 记忆管理

- 现状：
  - memory supersede 与唯一键冲突路径已修复并回归通过；
  - 记忆写入与回忆具备治理层（质量、保留策略、引用证据）。
- 对比：
  - 对齐 Mem0/OpenViking 外部 backbone 复用思路；
  - 比“纯向量召回”方案更适合审计与生产责任归因。
- 结论：memory 主干合理，下一步重点是在线质量评分与业务指标闭环。

## 3. 本轮 TODO 收口（已完成）

1. `memory supersede` 与唯一键冲突：
   - 已修复并通过回归：`tests/test_memory_supersede_conflict.py`。
2. `depends_on` 真正 DAG + `max_attempts` + 退避策略：
   - 已落地并通过回归：`tests/test_workflow_task_graph_and_retry.py`。
3. `ContextAssemblyService` 接入 runtime 默认 dispatch 路径：
   - 已接入并通过回归：`tests/test_t3_context_recall.py`、`tests/test_workflow_notification_metadata.py`。
4. 通知持久化复用现有域模型，避免重复实现：
   - 统一复用 `RuntimeNotificationDelivery`，补齐 `NotificationHistoryService` / recorder / query；
   - 通过回归：`tests/test_notification_persistence.py`、`tests/test_notification_product_surfaces.py`。
5. SLA 观测视图：
   - 增强 `runtime_sla_snapshot` 与 `/observability/runtime-sla`；
   - 对“轻量未建表场景”增加降级返回，避免接口炸裂；
   - 前端 `telemetry` 页面已接入 `use-runtime-sla`（SLA 概览 + 趋势）；
   - 通过回归：`tests/test_t7_observability.py`、`apps/web/tests/unit/observability/run-telemetry-screen.test.tsx`。

## 4. Query 唤起 goofish-insight 自迭代实测

- 实测入口：`POST /runtime/runs/start`
- 运行号：`run-goofish-self-1776907799`
- 结果证据：
  - `graph_nodes = 10`
  - `graph_edges = 9`
  - 命中 `loop-1-survey` 与 `loop-2-review` 节点
  - `timeline_entries = 8`（已出现任务执行推进）
- 结论：query 已能稳定唤起 `project.improvement(self_driven, loop_iterations=2)` 自迭代链路。
- 2026-04-23 追加复验：`tests/test_temporal_runtime_approval.py -k goofish_query` 通过。
- 2026-04-23 发布门复验：`pnpm lint && pnpm typecheck && pnpm test` 全绿（`api 157 passed, 8 skipped`；`web 22 passed`）。

## 5. 仍建议的下一步（P2，不阻断）

1. 在 SLA 面板补“按 workflow_name / executor / project 分组”的趋势线。
2. 增加 notification 投递失败分类（鉴权失败、目标缺失、网络超时）并接入告警阈值。
3. 为自迭代环新增“轮次收益”指标（每轮缺陷收敛、任务完成率、人工审批占比）。
4. 完成飞书通知生产配置（启用开关 + app 凭据 + receive_id），将“链路完成”通知纳入标准发布 SOP。
