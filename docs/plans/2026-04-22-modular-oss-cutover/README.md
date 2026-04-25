# ai-desk 模块化与 OSS 收口计划

- 日期：`2026-04-22`
- 仓库：`/Users/admin/Desktop/ai-desk`
- 目标：把 `ai-desk` 从“强架构原型”收口到“模块清晰、默认安全、优先复用成熟 OSS”的工程化平台

---

## 1. 当前判断

当前仓库不再适合继续以“局部修补 + 自定义桥接”方式扩展。

后续主线应固定为：

1. 按模块收口，而不是按目录堆代码
2. 通用基础设施优先接热门、持续维护的 GitHub OSS
3. `ai-desk` 只保留 control plane、review surface、project loop 等差异化能力

---

## 2. 模块目标结构

目标结构：

```text
apps/api/api/modules/
  control_plane/
  runtime/
  execution/
  memory/
  review/
  notifications/
  integrations/
    temporal/
    langgraph/
    openhands/
    mem0/
    feishu/
```

约束：

- 领域模块不直接引用第三方 SDK 细节
- 第三方系统接入统一收敛到 `integrations/*`
- `app.py` 只做模块注册与容器装配
- `dependencies.py` 不再承担跨领域总装配角色

---

## 3. OSS 选型冻结

### A. Durable orchestration

- 采用：`Temporal`
- 保留原因：已经是当前 runtime 主调度面，且 workflow/event history/retry/signal 语义不值得自研

### B. Agent graph persistence

- 采用：`LangGraph` 官方 checkpointer / persistence
- 禁止：继续长期维护自定义 checkpoint save/resume 语义

### C. Executor runtime / sandbox

- 采用：`OpenHands` 官方 runtime architecture
- 禁止：继续扩大私有 `/api/execute` bridge 协议面

### D. Memory backbone

- 默认采用：`Mem0`
- 条件采用：`Letta`

选择规则：

- 需要基础记忆设施：优先 `Mem0`
- 需要 agent-visible core memory block：再评估 `Letta`

---

## 4. P0 任务

### P0-1 取消全局 full access

目标：

- 移除进程级 `runtime_full_access_enabled` 作为默认执行路径
- 改成 run 级 capability grant

验收：

- 默认策略恢复 least privilege
- `.env.local` 不再改变测试语义
- approval 与安全测试恢复稳定

### P0-2 Runtime / Execution 解耦

目标：

- `runtime` 只负责 run/task/attempt/claim/event/projector/recovery
- `execution` 只负责 dispatch/provider/transport/contracts

验收：

- workflow 不再直接揉合 security/context/review/execution 细节
- execution 依赖装配不再横向抓 runtime/memory/review 内部实现

### P0-3 Approval bridge durable 化

目标：

- executor 发起审批时，workflow 进入 pause/waiting 状态
- 审批通过后 resume，而不是 `approval_bridge_missing`

验收：

- `approval required -> resolve -> resume -> complete` 端到端可回归
- 重启后审批状态仍可恢复

### P0-4 切到官方 LangGraph persistence

目标：

- 用官方 checkpointer 取代 `RuntimeGraphService` 自定义 checkpoint 流程

验收：

- interrupt / resume / replay 走官方持久化能力
- 重启恢复不依赖内存态或手工 dict state

### P0-5 用官方 OpenHands runtime 收口 execution integration

目标：

- adapter 保留在 `ai-desk`
- runtime 协议与 sandbox 语义对齐 OpenHands

验收：

- 删除私有 bridge DTO 的长期依赖
- provider 层只做 mapping，不再定义第二套 runtime 协议

---

## 5. P1 任务

### P1-1 Memory 切到 Mem0

目标：

- `memory` 模块仅保留 governance / evidence / namespace policy
- recall / persist / layering 交给 `Mem0`

验收：

- context recall 通过 memory adapter 获取
- 不再以本地 dict 或手写 ranking 作为长期 backbone

### P1-2 Integrations 收口

目标：

- `Feishu`、`OpenHands health probe`、`Mem0 client`、`Temporal client` 统一归到 `integrations/*`

验收：

- 不再出现 health/router 依赖 memory/openviking 这类边界反转

### P1-3 测试与契约恢复为发布门

目标：

- `pnpm test` 稳定全绿
- snapshot 漂移只在明确 contract 变更时发生

验收：

- approval / restart durability / openapi snapshot 回归稳定

---

## 6. 执行顺序

建议顺序：

1. `P0-1` 取消全局 full access
2. `P0-3` 打通 durable approval bridge
3. `P0-2` Runtime / Execution 解耦
4. `P0-4` LangGraph persistence official cutover
5. `P0-5` OpenHands runtime official cutover
6. `P1-1` Memory 切 Mem0
7. `P1-2` Integrations 收口
8. `P1-3` 回归体系稳定化

原因：

- 先恢复默认安全和测试可信度
- 再替换 durability 与 runtime 主路径
- 最后做 memory backbone 与边界净化

---

## 7. 发布门

满足以下条件，才可再次声称“接近最佳实践完成态”：

1. `pnpm test` 全绿
2. approval e2e 与 restart durability e2e 全绿
3. 默认模式为 least privilege
4. LangGraph durability 不再是自定义语义
5. OpenHands runtime 不再依赖私有长期 bridge
6. memory backbone 已切到正式外部系统

---

## 8. 关联文档

- [modular-boundaries-and-oss-adoption.md](/Users/admin/Desktop/ai-desk/docs/specs/modular-boundaries-and-oss-adoption.md)
- [README.md](/Users/admin/Desktop/ai-desk/docs/plans/2026-04-19-ai-desk-closure-plan/README.md)
