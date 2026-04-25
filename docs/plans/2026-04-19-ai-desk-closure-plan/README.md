# ai-desk 收口状态总表

- 日期：`2026-04-19`
- 仓库：`/Users/admin/Desktop/ai-desk`
- 目标：四块核心能力闭合并进入收口验收

---

## 0. 现实校准（2026-04-22）

本文件最初记录的是 `2026-04-19` 阶段性收口结论，不应继续被视为“当前仓库已完全闭合”的事实证明。

按 `2026-04-22` 的仓库与回归结果重新校准：

- `pnpm test` 当前不是全绿，最新本地结果为：`125 passed, 8 skipped, 7 failed`
- `full access` 仍是进程级总开关，不符合 `safe-by-default`
- approval 仍未形成真正的 durable pause/resume bridge
- LangGraph durability 仍以自定义 checkpoint 流程为主，未完全切到官方持久化路径
- OpenHands 仍保留自定义 `/api/execute` bridge，未完全对齐官方 runtime architecture

因此，本计划目录中的任务文档应理解为：

- `2026-04-19` 阶段的实现与验收记录
- 不是 `2026-04-22` 的最终最佳实践完成态声明

后续收口基线以以下文档为准：

- [modular-boundaries-and-oss-adoption.md](/Users/admin/Desktop/ai-desk/docs/specs/modular-boundaries-and-oss-adoption.md)
- `2026-04-22` 之后的新回归结果

---

## 1. 当前结论

核心四块已落地并通过本地回归：

1. durable runtime（Temporal + runtime persistence）  
2. state truth source（Postgres runtime/review/memory/security 表）  
3. memory backbone（治理 + recall + OpenViking adapter + context 集成）  
4. executor runtime（Codex/OpenHands transport + approval/verification/provenance 路径）

当前状态：`2026-04-19 阶段性收口完成`。  
说明：该结论仅对应当时的阶段性实现记录，不能替代后续回归与最佳实践校准。

---

## 2. 任务闭合状态

- `T1` Review durability：`已闭合`
- `T2` Runtime durable semantics：`已闭合`
- `T3` Context recall integration：`已闭合`
- `T4` Memory governance backbone：`已闭合`
- `T5` Executor live integration：`已闭合（含 live smoke 门控）`
- `T6` Security hardening：`已闭合`
- `T7` Observability + runbook：`已闭合`
- `T8` E2E + contract regression：`已闭合`

---

## 3. 历史验证结果（2026-04-19）

- `pnpm --dir /Users/admin/Desktop/ai-desk lint`：通过
- `pnpm --dir /Users/admin/Desktop/ai-desk typecheck`：通过
- `pnpm --dir /Users/admin/Desktop/ai-desk test`：通过  
  `@ai-desk/api: 105 passed, 8 skipped`  
  `@ai-desk/web: 22 passed`
- migration 检查：通过（upgrade to head 与核心表验证通过）
- contracts/openapi 快照：已更新并回归通过

补充：

- `2026-04-22` 重新执行 `pnpm test` 时，结果已发生漂移，见本文件“现实校准”部分

---

## 4. 任务文档索引

- [T1-review-durability.md](/Users/admin/Desktop/ai-desk/docs/plans/2026-04-19-ai-desk-closure-plan/T1-review-durability.md)
- [T2-runtime-durable-semantics.md](/Users/admin/Desktop/ai-desk/docs/plans/2026-04-19-ai-desk-closure-plan/T2-runtime-durable-semantics.md)
- [T3-context-recall-integration.md](/Users/admin/Desktop/ai-desk/docs/plans/2026-04-19-ai-desk-closure-plan/T3-context-recall-integration.md)
- [T4-memory-governance-backbone.md](/Users/admin/Desktop/ai-desk/docs/plans/2026-04-19-ai-desk-closure-plan/T4-memory-governance-backbone.md)
- [T5-executor-live-integration.md](/Users/admin/Desktop/ai-desk/docs/plans/2026-04-19-ai-desk-closure-plan/T5-executor-live-integration.md)
- [T6-security-hardening.md](/Users/admin/Desktop/ai-desk/docs/plans/2026-04-19-ai-desk-closure-plan/T6-security-hardening.md)
- [T7-observability-and-runbook.md](/Users/admin/Desktop/ai-desk/docs/plans/2026-04-19-ai-desk-closure-plan/T7-observability-and-runbook.md)
- [T8-e2e-and-contract-regression.md](/Users/admin/Desktop/ai-desk/docs/plans/2026-04-19-ai-desk-closure-plan/T8-e2e-and-contract-regression.md)
