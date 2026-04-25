# T1 Review Durability 收口

- 优先级：`P0`
- 目标：把 approval 之外剩余的 review 主数据从内存态切到持久化，关闭 attempt / evidence 的 durable 缺口

---

## 1. 当前问题

当前 review 面并没有完全 durable：

- `EvidenceService` 只存在进程内 dict：
  - `/Users/admin/Desktop/ai-desk/apps/api/api/review/service.py:293`
- `AttemptStore` 只存在进程内 dict：
  - `/Users/admin/Desktop/ai-desk/apps/api/api/review/service.py:356`

这意味着：

1. API 进程重启后，attempt summary 会丢。
2. evidence summary 会丢。
3. FE-2 / FE-3 看到的 attempt / evidence 不是 durable truth。
4. executor dispatch 与 review read side 没有真正闭合。

---

## 2. 技术实施方案

### A. 增加持久化模型

在 `/Users/admin/Desktop/ai-desk/apps/api/api/runtime_persistence/models.py` 中新增：

1. `RuntimeAttemptSummary`
2. `RuntimeEvidenceSummary`
3. `RuntimeVerificationRecord`
4. `RuntimeProvenanceGraphSnapshot`

建议字段：

- `attempt_summaries`
  - `id`
  - `workflow_run_id`
  - `task_id`
  - `project_id`
  - `executor_type`
  - `status`
  - `failure_category`
  - `failure_reason`
  - `started_at`
  - `ended_at`
  - `approval_id`
  - `verification_passed`
  - `linked_artifact_ids_json`
  - `linked_evidence_refs_json`
  - `provenance_json`
  - `metadata_json`

- `evidence_summaries`
  - `attempt_id`
  - `artifact_ids_json`
  - `verification_json`
  - `verification_refs_json`
  - `memory_refs_json`
  - `provenance_graph_json`

### B. 增加 migration

新增 Alembic migration：

- 新建上述 2 到 4 张表
- 给 `attempt_id / workflow_run_id / task_id / project_id` 建索引

### C. 重写 review service

重构 `/Users/admin/Desktop/ai-desk/apps/api/api/review/service.py`：

1. `AttemptStore` 改成 DB-backed service
2. `EvidenceService` 改成 DB-backed service
3. 保留 in-memory fallback 仅用于纯单测，不再作为默认主路径

### D. 接入 execution container

更新 `/Users/admin/Desktop/ai-desk/apps/api/api/executors/dependencies.py`：

1. 默认注入 `session_factory`
2. review container 全部使用持久化 service

### E. Read API 对齐

确认 `/Users/admin/Desktop/ai-desk/apps/api/api/review/router.py` 读取的是持久化结果，不再依赖内存对象。

---

## 3. 验收标准

1. `POST /executors/dispatch` 产生的 attempt 与 evidence 可在进程重启后继续查询。
2. `GET /review/evidence/{attempt_id}` 可从 DB 恢复。
3. `GET /review/attempts` / `GET /review/attempts/{attempt_id}` 可从 DB 恢复。
4. review 相关测试新增 durable case。

---

## 4. 建议测试

1. dispatch 一次执行，查询 attempt/evidence 成功。
2. 重建 app / session 后再次查询，结果仍存在。
3. approval-waiting attempt 能落库。
4. failed / retryable / succeeded 三种 attempt 都能正确映射。
