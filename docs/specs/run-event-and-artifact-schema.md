# Run Event And Artifact Schema

- 状态：`Working Draft (v0.3, 2026-04-19)`

## 当前已落地 schema（代码已实现）

1. run event envelope（event_id / sequence / correlation / payload / idempotency_key）
2. timeline read model（按 `workflow_run_id` 投影）
3. task graph read model（nodes/edges）
4. attempt history read model
5. worker health read model
6. artifact/evidence 关联（attempt -> artifact_ids + evidence summary）

## 仍待冻结主题

1. payload_version 的严格迁移策略
2. artifact metadata 的最小标准字段（跨 executor）
3. evidence linkage 的反向索引（artifact -> attempts）
4. trace/span 与 run events 的统一主键策略

## 对应代码落点

- `apps/api/api/events/models.py`
- `apps/api/api/events/builder.py`
- `apps/api/api/runtime_persistence/models.py`
- `apps/api/api/runtime_persistence/projectors.py`
- `apps/api/api/review/service.py`
