# T2 Runtime Durable Semantics 收口

- 优先级：`P0`
- 目标：把 runtime 从“已持久化基础表”推进到“语义真正 durable”，补上 lease、恢复、调度、读模型一致性缺口

---

## 1. 当前问题

虽然 runtime 表和 Temporal 主路径已经存在，但语义还没有完全闭合：

1. heartbeat 只打了一次，不是持续续租：
   - `/Users/admin/Desktop/ai-desk/apps/api/api/workflows/definitions/base.py:194`
2. stale reclaim 主要靠显式调用 activity，不是统一后台恢复策略：
   - `/Users/admin/Desktop/ai-desk/apps/api/api/workflows/definitions/base.py:207`
3. `/runtime/dev/bootstrap` 仍然保留为主测试入口，容易掩盖真实 runtime path：
   - `/Users/admin/Desktop/ai-desk/apps/api/api/workflows/router.py:32`
4. runtime read model 仍然部分依赖 event replay 推导，而不是完整 projector/read model 体系：
   - `/Users/admin/Desktop/ai-desk/apps/api/api/runtime_persistence/service.py`

---

## 2. 技术实施方案

### A. 补持续 lease 机制

在 workflow 主执行链中新增 heartbeat loop：

1. 在 `execute_task` 内启动 heartbeat child task 或周期 activity
2. 直到任务完成、失败、reclaimed、cancelled 后停止
3. 每次 heartbeat 更新：
   - `task_claims.heartbeat_at`
   - `run_events` 中的 `task.heartbeat`

代码落点：

- `/Users/admin/Desktop/ai-desk/apps/api/api/workflows/definitions/base.py`
- `/Users/admin/Desktop/ai-desk/apps/api/api/workflows/activities/runtime_activities.py`

### B. 增加 runtime recovery job

新增恢复入口：

1. 扫描 stale active claims
2. 把对应 task / attempt 标记为 `reclaimed`
3. 对 workflow 状态做恢复决策：
   - retry
   - fail
   - requeue

代码落点：

- 新增 `/Users/admin/Desktop/ai-desk/apps/api/api/workflows/recovery.py`
- 可由 worker 启动时、定时任务或管理 API 调用

### C. 切分 bootstrap 与真实入口

1. 保留 `/runtime/dev/bootstrap` 仅供测试或 dev fixture
2. 在 README 与 runbook 中明确：
   - 正式入口是 `/runtime/runs/start`
   - bootstrap 不是生产语义

### D. 建 runtime projector/read model 服务

新增显式 projector 层：

1. `TimelineProjector`
2. `TaskGraphProjector`
3. `AttemptHistoryProjector`
4. `WorkerHealthProjector`

从 `RuntimePersistenceService` 中拆出投影逻辑，避免一个 service 同时承担：

1. write side
2. event append
3. read model build
4. lease logic

### E. workflow 启动与恢复测试

补真正基于 `/runtime/runs/start` 的测试，而不是只测 bootstrap。

---

## 3. 验收标准

1. task 运行期间有持续 heartbeat 更新。
2. stale claim 可被 recovery job 自动收敛。
3. `/runtime/runs/start` 成为主测试入口。
4. runtime read models 可由投影层稳定构建。

---

## 4. 建议测试

1. heartbeat 在长任务期间更新多次。
2. 模拟 worker crash 后，recovery job 能把 claim 回收。
3. workflow restart 后 timeline / graph / attempts 仍一致。
4. 真实 start path 的 API 测试通过。
