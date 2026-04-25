# Memory Governance And Evaluation

- 状态：`Working Draft (v0.3, 2026-04-19)`

## 当前已落地语义（代码已实现）

1. memory write governance（threshold + dedup + merge/supersede）
2. DB 持久化主存储（`memory_records`）
3. OpenViking adapter（写入与检索，失败降级）
4. recall ranking（score/quality/evidence/recency 混合）
5. recall stats 更新（`recall_count` / `last_recalled_at`）

## 仍待冻结主题

1. retention lifecycle（decay/archival）后台作业策略
2. retrieval evaluation 指标与离线回放集
3. cross-project / global namespace 的治理边界
4. write-back to external memory 的幂等与补偿策略

## 对应代码落点

- `apps/api/api/memory/service.py`
- `apps/api/api/memory/governance.py`
- `apps/api/api/memory/ranking.py`
- `apps/api/api/memory/openviking.py`
