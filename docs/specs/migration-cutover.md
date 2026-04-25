# Migration Cutover

- 状态：`Working Draft (v0.3, 2026-04-19)`

## 当前状态

1. runtime / memory / security / review 关键表迁移已存在（alembic 0001~0004）
2. app 启动默认依赖已包含 migration 执行路径（`pnpm dev` -> migrate）
3. E2E 已覆盖 restart durability 核心用例

## 仍待冻结主题

1. backfill strategy
2. dual-write policy
3. cutover gate
4. rollback plan
5. data validation and reconciliation
6. freeze window
7. legacy read model policy

## 当前建议 cutover gate（草案）

1. API+Web 单仓回归全绿（单元 + e2e）
2. runtime/review/memory restart durability 用例全绿
3. 本地 runbook 端到端可演练（infra up -> worker -> run -> review）
4. event/contract snapshot 无 breaking diff 或 diff 已审批

## 对应代码落点

- `apps/api/alembic/versions/20260419_0001_bootstrap.py`
- `apps/api/alembic/versions/20260419_0002_runtime_backbone.py`
- `apps/api/alembic/versions/20260419_0003_memory_governance.py`
- `apps/api/alembic/versions/20260419_0003a_security_hardening.py`
- `apps/api/alembic/versions/20260419_0004_review_durability.py`
