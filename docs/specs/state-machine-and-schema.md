# State Machine And Schema

- 状态：`Working Draft (v0.3, 2026-04-19)`

## 当前已落地状态机（代码已实现）

1. `workflow_runs.status`: created/queued/running/waiting_approval/retrying/completed/failed/cancelled
2. `tasks.status`: queued/claimed/running/verifying/retrying/completed/failed/reclaimed/cancelled
3. `task_claims.status`: active/released/reclaimed/expired（recovery）
4. `approvals.status`: pending/approved/rejected/expired/cancelled
5. `attempt_summaries.status`: waiting_approval/completed/failed_retryable/failed_terminal/cancelled

## 关键表（runtime persistence）

1. `workflow_runs`
2. `tasks`
3. `task_attempts`
4. `task_claims`
5. `run_events`
6. `approvals`
7. `attempt_summaries`
8. `evidence_summaries`
9. `artifacts`
10. `memory_records`

## 仍待冻结主题

1. `workspace_allocations`（尚未建模）
2. retry 计数与回退策略的持久化字段
3. duplicate dispatch 的跨 provider 幂等策略细化
4. claim reclaim 后自动重试 vs fail-fast 的策略边界

## 对应代码落点

- `apps/api/api/runtime_persistence/models.py`
- `apps/api/api/runtime_persistence/service.py`
- `apps/api/api/workflows/state_machine.py`
- `apps/api/api/review/service.py`
