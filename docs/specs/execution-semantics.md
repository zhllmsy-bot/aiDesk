# Execution Semantics

- 状态：`Working Draft (v0.3, 2026-04-19)`

## 当前已落地语义（代码已实现）

1. Runtime 工作流启动路径
2. Task claim / heartbeat / release / reclaim 生命周期
3. Approval gating（任务级等待批准）
4. Executor dispatch -> artifact/attempt/evidence 写入
5. Workflow/Task 状态转换活动（activity 驱动）
6. `project.audit` 默认三段式评估（Survey / Counter-argument / Roadmap）
7. `project.improvement` 双驱动模式（self_driven / external_requirement）

## 仍待冻结主题

1. workflow start/stop semantics
2. retry and reclaim boundary
3. approval pause / resume semantics
4. executor result merge policy

## 对应代码落点

- `apps/api/api/workflows/definitions/base.py`
- `apps/api/api/workflows/definitions/project_audit.py`
- `apps/api/api/workflows/definitions/project_improvement.py`
- `apps/api/api/workflows/activities/runtime_activities.py`
- `apps/api/api/workflows/router.py`
- `apps/api/api/executors/service.py`
- `apps/api/api/review/service.py`
